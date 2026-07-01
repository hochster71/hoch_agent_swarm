import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

function computeSha256(filePath: string): string {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(content).digest('hex');
}

function verifyNoDriftCurrentState() {
  console.log("==================================================");
  console.log("RUNNING CURRENT-STATE DRIFT DETECTOR");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const registerPath = path.join(baseDir, 'artifacts/production-readiness-final-candidate-seal/visual-control-plane-local-v1/production_no_drift_checksum_register.json');

  if (!fs.existsSync(registerPath)) {
    console.error(`Checksum lock register does not exist at: ${registerPath}`);
    process.exit(1);
  }

  let failed = false;
  let registerObj: any;

  try {
    registerObj = JSON.parse(fs.readFileSync(registerPath, 'utf-8'));
  } catch (e: any) {
    console.error(`Failed to parse register: ${e.message}`);
    process.exit(1);
  }

  const reg = registerObj.checksum_register;
  if (!reg) {
    console.error("No checksum_register object found in register file.");
    process.exit(1);
  }

  const relativePaths = Object.keys(reg);
  console.log(`Locked File Register Count: ${relativePaths.length}`);

  relativePaths.forEach(relPath => {
    const fullPath = path.join(baseDir, relPath);
    const expectedSha = reg[relPath].sha256;

    if (!fs.existsSync(fullPath)) {
      console.error(`[FAIL] Missing locked file: ${relPath}`);
      failed = true;
      return;
    }

    try {
      const currentSha = computeSha256(fullPath);
      if (currentSha !== expectedSha) {
        console.error(`[FAIL] Drift detected in: ${relPath}`);
        console.error(`       Expected: ${expectedSha}`);
        console.error(`       Current:  ${currentSha}`);
        failed = true;
      } else {
        console.log(`[PASS] ${relPath} matches checksum lock`);
      }
    } catch (e: any) {
      console.error(`[FAIL] Error computing hash for ${relPath}: ${e.message}`);
      failed = true;
    }
  });

  console.log("==================================================");
  if (failed) {
    console.error("CURRENT-STATE DRIFT DETECTOR FAILED: Drift or missing files detected.");
    process.exit(1);
  } else {
    console.log("CURRENT-STATE DRIFT DETECTOR PASSED SUCCESSFULLY: Zero drift detected.");
    process.exit(0);
  }
}

verifyNoDriftCurrentState();
