/*
 * This file is part of Hadoop-Gpl-Compression.
 *
 * Hadoop-Gpl-Compression is free software: you can redistribute it
 * and/or modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.
 *
 * Hadoop-Gpl-Compression is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty
 * of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Hadoop-Gpl-Compression.  If not, see
 * <http://www.gnu.org/licenses/>.
 */

package com.hadoop.compression.lzo;

import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.zip.Adler32;
import java.util.zip.CRC32;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.apache.hadoop.io.compress.BlockDecompressorStream;
import org.apache.hadoop.io.compress.CodecPool;
import org.apache.hadoop.io.compress.Decompressor;

public class LzopInputStream extends BlockDecompressorStream {

  private static final Log LOG = LogFactory.getLog(LzopInputStream.class);

  private final EnumSet<DChecksum> dflags = EnumSet.allOf(DChecksum.class);
  private final EnumSet<CChecksum> cflags = EnumSet.allOf(CChecksum.class);

  private final byte[] buf = new byte[9];
  private final EnumMap<DChecksum,Integer> dcheck = new EnumMap<DChecksum,Integer>(DChecksum.class);
  private final EnumMap<CChecksum,Integer> ccheck = new EnumMap<CChecksum,Integer>(CChecksum.class);

  private int noUncompressedBytes = 0;
  private int noCompressedBytes = 0;
  private int uncompressedBlockSize = 0;
  private boolean closed = false;

  public LzopInputStream(InputStream in, Decompressor decompressor,
      int bufferSize) throws IOException {
    super(in, decompressor, bufferSize);
    readHeader(in);
  }

  /**
   * Reads len bytes in a loop.
   *
   * This is copied from IOUtils.readFully except that it throws an EOFException
   * instead of generic IOException on EOF.
   *
   * @param in The InputStream to read from
   * @param buf The buffer to fill
   * @param off offset from the buffer
   * @param len the length of bytes to read
   */
  private static void readFully( InputStream in, byte buf[],
      int off, int len ) throws IOException, EOFException {
    int toRead = len;
    while ( toRead > 0 ) {
      int ret = in.read( buf, off, toRead );
      if ( ret < 0 ) {
        throw new EOFException("Premature EOF from inputStream");
      }
      if ( ret == 0 ) {
        throw new IOException("Input stream made no progress while reading " +
          len + " bytes");
      }
      toRead -= ret;
      off += ret;
    }
  }

  /**
   * Read len bytes into buf, st LSB of int returned is the last byte of the
   * first word read.
   */
  private static int readInt(InputStream in, byte[] buf, int len)
  throws IOException {
    readFully(in, buf, 0, len);
    int ret = (0xFF & buf[0]) << 24;
    ret    |= (0xFF & buf[1]) << 16;
    ret    |= (0xFF & buf[2]) << 8;
    ret    |= (0xFF & buf[3]);
    return (len > 3) ? ret : (ret >>> (8 * (4 - len)));
  }

  static long readNextBlockSize(InputStream in, byte[] blockSizeBuffer)
  throws IOException {
    readFully(in, blockSizeBuffer, 0, 4);
    return ((long)(0xFF & blockSizeBuffer[0]) << 24)
      | ((long)(0xFF & blockSizeBuffer[1]) << 16)
      | ((long)(0xFF & blockSizeBuffer[2]) << 8)
      | (long)(0xFF & blockSizeBuffer[3]);
  }

  static void validateDecompressedLength(int decompressed, int consumed,
      int expected) throws IOException {
    if (decompressed < 0) {
      throw new IOException("Decompressor returned a negative byte count");
    }
    if (consumed > expected - decompressed) {
      throw new IOException("Decompressed block exceeds declared length " +
        expected + " (probably corrupt file)");
    }
  }

  static int limitDecompressionLength(int requested, int consumed, int expected)
  throws IOException {
    if (consumed < 0 || consumed > expected) {
      throw new IOException("Invalid decompressed block position " + consumed);
    }
    return Math.min(requested, expected - consumed);
  }

  static void validateHeaderFlags(int flags) throws IOException {
    if ((flags & ~0x00003FFF) != 0) {
      throw new IOException("Unknown flags in header");
    }
  }

  static void readHeaderBytes(InputStream in, int len, Adler32 adler,
      CRC32 crc32) throws IOException {
    byte[] headerBuffer = new byte[Math.min(8192, Math.max(1, len))];
    int remaining = len;
    while (remaining > 0) {
      int chunk = Math.min(headerBuffer.length, remaining);
      readFully(in, headerBuffer, 0, chunk);
      adler.update(headerBuffer, 0, chunk);
      crc32.update(headerBuffer, 0, chunk);
      remaining -= chunk;
    }
  }

  /**
   * Read bytes, update checksums, return first four bytes as an int, first
   * byte read in the MSB.
   */
  private static int readHeaderItem(InputStream in, byte[] buf, int len,
      Adler32 adler, CRC32 crc32) throws IOException {
    int ret = readInt(in, buf, len);
    adler.update(buf, 0, len);
    crc32.update(buf, 0, len);
    Arrays.fill(buf, (byte)0);
    return ret;
  }

  /**
   * Read and verify an lzo header, setting relevant block checksum options
   * and ignoring most everything else.
   */
  protected void readHeader(InputStream in) throws IOException {
    readFully(in, buf, 0, 9);
    if (!Arrays.equals(buf, LzopCodec.LZO_MAGIC)) {
      throw new IOException("Invalid LZO header");
    }
    Arrays.fill(buf, (byte)0);
    Adler32 adler = new Adler32();
    CRC32 crc32 = new CRC32();
    int hitem = readHeaderItem(in, buf, 2, adler, crc32); // lzop version
    if (hitem > LzopCodec.LZOP_VERSION) {
      LOG.debug("Compressed with later version of lzop: " +
          Integer.toHexString(hitem) + " (expected 0x" +
          Integer.toHexString(LzopCodec.LZOP_VERSION) + ")");
    }
    hitem = readHeaderItem(in, buf, 2, adler, crc32); // lzo library version
    if (hitem < LzoDecompressor.MINIMUM_LZO_VERSION) {
      throw new IOException("Compressed with incompatible lzo version: 0x" +
          Integer.toHexString(hitem) + " (expected at least 0x" +
          Integer.toHexString(LzoDecompressor.MINIMUM_LZO_VERSION) + ")");
    }
    hitem = readHeaderItem(in, buf, 2, adler, crc32); // lzop extract version
    if (hitem > LzopCodec.LZOP_VERSION) {
      throw new IOException("Compressed with incompatible lzop version: 0x" +
          Integer.toHexString(hitem) + " (expected 0x" +
          Integer.toHexString(LzopCodec.LZOP_VERSION) + ")");
    }
    hitem = readHeaderItem(in, buf, 1, adler, crc32); // method
    if (hitem < 1 || hitem > 3) {
      throw new IOException("Invalid strategy: " +
          Integer.toHexString(hitem));
    }
    readHeaderItem(in, buf, 1, adler, crc32); // ignore level

    // flags
    hitem = readHeaderItem(in, buf, 4, adler, crc32);
    validateHeaderFlags(hitem);
    try {
      for (DChecksum f : dflags) {
        if (0 == (f.getHeaderMask() & hitem)) {
          dflags.remove(f);
        } else {
          dcheck.put(f, (int)f.getChecksumClass().newInstance().getValue());
        }
      }
      for (CChecksum f : cflags) {
        if (0 == (f.getHeaderMask() & hitem)) {
          cflags.remove(f);
        } else {
          ccheck.put(f, (int)f.getChecksumClass().newInstance().getValue());
        }
      }
    } catch (InstantiationException e) {
      throw new RuntimeException("Internal error", e);
    } catch (IllegalAccessException e) {
      throw new RuntimeException("Internal error", e);
    }
    ((LzopDecompressor)decompressor).initHeaderFlags(dflags, cflags);
    boolean useCRC32 = 0 != (hitem & 0x00001000);   // F_H_CRC32
    boolean extraField = 0 != (hitem & 0x00000040); // F_H_EXTRA_FIELD
    if (0 != (hitem & 0x400)) {                     // F_MULTIPART
      throw new IOException("Multipart lzop not supported");
    }
    if (0 != (hitem & 0x800)) {                     // F_H_FILTER
      throw new IOException("lzop filter not supported");
    }
    // known !F_H_FILTER, so no optional block

    readHeaderItem(in, buf, 4, adler, crc32); // ignore mode
    readHeaderItem(in, buf, 4, adler, crc32); // ignore mtime
    readHeaderItem(in, buf, 4, adler, crc32); // ignore gmtdiff
    hitem = readHeaderItem(in, buf, 1, adler, crc32); // fn len
    if (hitem > 0) {
      // skip filename
      int filenameLen = Math.max(4, hitem); // buffer must be at least 4 bytes for readHeaderItem to work.
      readHeaderItem(in, new byte[filenameLen], hitem, adler, crc32);
    }
    int checksum = (int)(useCRC32 ? crc32.getValue() : adler.getValue());
    hitem = readHeaderItem(in, buf, 4, adler, crc32); // read checksum
    if (hitem != checksum) {
      throw new IOException("Invalid header checksum: " +
          Long.toHexString(checksum) + " (expected 0x" +
          Integer.toHexString(hitem) + ")");
    }
    if (extraField) { // lzop 1.08 ultimately ignores this
      LOG.debug("Extra header field not processed");
      adler.reset();
      crc32.reset();
      hitem = readHeaderItem(in, buf, 4, adler, crc32);
      int extraFieldLength =
        LzopHeaderValidation.validateExtraFieldLength(hitem);
      readHeaderBytes(in, extraFieldLength, adler, crc32);
      checksum = (int)(useCRC32 ? crc32.getValue() : adler.getValue());
      if (checksum != readHeaderItem(in, buf, 4, adler, crc32)) {
        throw new IOException("Invalid checksum for extra header field");
      }
    }
  }

  /**
   * Take checksums recorded from block header and verify them against
   * those recorded by the decomrpessor.
   */
  private void verifyChecksums() throws IOException {
    LzopDecompressor ldecompressor = ((LzopDecompressor)decompressor);
    for (Map.Entry<DChecksum,Integer> chk : dcheck.entrySet()) {
      if (!ldecompressor.verifyDChecksum(chk.getKey(), chk.getValue())) {
        throw new IOException("Corrupted uncompressed block");
      }
    }
    if (!ldecompressor.isCurrentBlockUncompressed()) {
      for (Map.Entry<CChecksum,Integer> chk : ccheck.entrySet()) {
        if (!ldecompressor.verifyCChecksum(chk.getKey(), chk.getValue())) {
          throw new IOException("Corrupted compressed block");
        }
      }
    }
  }

  @Override
  protected int decompress(byte[] b, int off, int len) throws IOException {
    // Check if we are the beginning of a block
    if (noUncompressedBytes == uncompressedBlockSize) {
      if (uncompressedBlockSize > 0) {
        verifyChecksums();
      }
      // Get original data size
      byte[] tempBuf = new byte[4];
      long nextBlockSize = readNextBlockSize(in, tempBuf);
      noCompressedBytes += 4;
      if (nextBlockSize == 0) {
        eof = true;
        return -1;
      } else if (nextBlockSize > LzoCodec.MAX_BLOCK_SIZE) {
        throw new IOException("Uncompressed length " + nextBlockSize +
          " exceeds max block size " + LzoCodec.MAX_BLOCK_SIZE +
          " (probably corrupt file)");
      }
      uncompressedBlockSize = (int)nextBlockSize;
      noUncompressedBytes = 0;
    }

    int n = 0;
    int limitedLength = limitDecompressionLength(len, noUncompressedBytes,
      uncompressedBlockSize);
    while ((n = decompressor.decompress(b, off, limitedLength)) == 0) {
      if (decompressor.finished() || decompressor.needsDictionary()) {
        if (noUncompressedBytes >= uncompressedBlockSize) {
          eof = true;
          return -1;
        }
      }
      requireInputAfterZeroProgress(decompressor);
      try {
        getCompressedData();
      } catch (EOFException e) {
        eof = true;
        return -1;
      } catch (IOException e) {
        LOG.warn("IOException in getCompressedData; likely LZO corruption.", e);
        throw e;
      }
    }

    // Note the no. of decompressed bytes read from 'current' block
    validateDecompressedLength(n, noUncompressedBytes, uncompressedBlockSize);
    noUncompressedBytes += n;

    return n;
  }

  static void requireInputAfterZeroProgress(Decompressor decompressor)
  throws IOException {
    if (!decompressor.needsInput()) {
      throw new IOException("Decompressor made no progress while reading");
    }
  }

  /**
   * Read checksums and feed compressed block data into decompressor.
   */
  @Override
  protected void getCompressedData() throws IOException {
    checkStream();

    // Get the size of the compressed chunk
    int compressedLen = readInt(in, buf, 4);
    noCompressedBytes += 4;

    if (compressedLen <= 0) {
      throw new IOException("Compressed length " + compressedLen +
        " must be positive (probably corrupt file)");
    }

    if (compressedLen > LzoCodec.MAX_BLOCK_SIZE) {
      throw new IOException("Compressed length " + compressedLen +
        " exceeds max block size " + LzoCodec.MAX_BLOCK_SIZE +
        " (probably corrupt file)");
    }

    if (compressedLen > uncompressedBlockSize) {
      throw new IOException("Compressed length " + compressedLen +
        " exceeds uncompressed length " + uncompressedBlockSize +
        " (probably corrupt file)");
    }

    LzopDecompressor ldecompressor = (LzopDecompressor)decompressor;
    // If the lzo compressor compresses a block of data, and that compression
    // actually makes the block larger, it writes the block as uncompressed instead.
    // In this case, the compressed size and the uncompressed size in the header
    // are identical, and there is NO compressed checksum written.
    ldecompressor.setCurrentBlockUncompressed(compressedLen == uncompressedBlockSize);

    for (DChecksum chk : dcheck.keySet()) {
      dcheck.put(chk, readInt(in, buf, 4));
      noCompressedBytes += 4;
    }

    if (!ldecompressor.isCurrentBlockUncompressed()) {
      for (CChecksum chk : ccheck.keySet()) {
        ccheck.put(chk, readInt(in, buf, 4));
        noCompressedBytes += 4;
      }
    }

    ldecompressor.resetChecksum();

    // Read len bytes from underlying stream
    if (compressedLen > buffer.length) {
      buffer = new byte[compressedLen];
    }
    readFully(in, buffer, 0, compressedLen);
    noCompressedBytes += compressedLen;

    // Send the read data to the decompressor.
    ldecompressor.setInput(buffer, 0, compressedLen);
  }

  public long getCompressedBytesRead() {
    return noCompressedBytes;
  }

  static void drainDecompressor(Decompressor decompressor) throws IOException {
    byte[] closeBuffer = new byte[4096];
    while (!decompressor.finished()) {
      int decompressed = decompressor.decompress(closeBuffer, 0,
        closeBuffer.length);
      if (decompressed <= 0) {
        if (decompressor.needsInput()) {
          return;
        }
        throw new IOException("Decompressor made no progress while closing " +
          "LzopInputStream");
      }
    }
  }

  @Override
  public void close() throws IOException {
    if (closed) {
      return;
    }
    closed = true;
    IOException closeFailure = null;
    try {
      drainDecompressor(decompressor);
    } catch (IOException e) {
      closeFailure = e;
    }
    try {
      super.close();
    } catch (IOException e) {
      if (closeFailure == null) {
        closeFailure = e;
      }
    }
    try {
      if (closeFailure == null) {
        verifyChecksums();
      }
    } catch (IOException e) {
      closeFailure = e;
    } finally{
      //return the decompressor to the pool, the function itself handles null.
      CodecPool.returnDecompressor(decompressor);
    }
    if (closeFailure != null) {
      throw closeFailure;
    }
  }
}
