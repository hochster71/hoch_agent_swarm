// engine/zip.js
//
// Minimal dependency-free ZIP writer (PKZIP local-file + central-directory,
// CRC-32, DEFLATE via node:zlib). Ported from the proven hff-hourly-rate
// packager so the XLSX writer needs no npm dependency.
'use strict';

const zlib = require('zlib');

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function buildZip(files) {
  const entries = [];
  const chunks = [];
  let offset = 0;

  for (const f of files) {
    const nameBuf = Buffer.from(f.name, 'utf8');
    const data = Buffer.isBuffer(f.data) ? f.data : Buffer.from(String(f.data), 'utf8');
    const crc = crc32(data);
    const comp = zlib.deflateRawSync(data);
    const useDeflate = comp.length < data.length;
    const method = useDeflate ? 8 : 0;
    const body = useDeflate ? comp : data;

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(method, 8);
    local.writeUInt16LE(0, 10);
    local.writeUInt16LE(0x21, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(body.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBuf.length, 26);
    local.writeUInt16LE(0, 28);

    chunks.push(local, nameBuf, body);
    entries.push({ nameBuf, crc, csize: body.length, usize: data.length, method, offset });
    offset += local.length + nameBuf.length + body.length;
  }

  const central = [];
  let cdSize = 0;
  for (const e of entries) {
    const hdr = Buffer.alloc(46);
    hdr.writeUInt32LE(0x02014b50, 0);
    hdr.writeUInt16LE(20, 4);
    hdr.writeUInt16LE(20, 6);
    hdr.writeUInt16LE(0, 8);
    hdr.writeUInt16LE(e.method, 10);
    hdr.writeUInt16LE(0, 12);
    hdr.writeUInt16LE(0x21, 14);
    hdr.writeUInt32LE(e.crc, 16);
    hdr.writeUInt32LE(e.csize, 20);
    hdr.writeUInt32LE(e.usize, 24);
    hdr.writeUInt16LE(e.nameBuf.length, 28);
    hdr.writeUInt16LE(0, 30);
    hdr.writeUInt16LE(0, 32);
    hdr.writeUInt16LE(0, 34);
    hdr.writeUInt16LE(0, 36);
    hdr.writeUInt32LE(0, 38);
    hdr.writeUInt32LE(e.offset, 42);
    central.push(hdr, e.nameBuf);
    cdSize += hdr.length + e.nameBuf.length;
  }

  const cdOffset = offset;
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(cdSize, 12);
  end.writeUInt32LE(cdOffset, 16);
  end.writeUInt16LE(0, 20);

  return Buffer.concat([...chunks, ...central, end]);
}

module.exports = { buildZip, crc32 };
