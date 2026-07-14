#!/usr/bin/env bash
# scripts/cloud/configure_helm_volume.sh
set -euo pipefail

# Print help and exit if required
EXECUTE_FLAG=${1:-""}

echo "=== HELM Block Storage Configuration System ==="

# 1. Discover root disk
ROOT_DEV=$(findmnt -n -o SOURCE /)
# Remove partition suffix to get base disk name (e.g. /dev/sda1 -> sda)
ROOT_DISK=$(echo "$ROOT_DEV" | sed -E 's|/dev/([a-z]+)[0-9]*|\1|')
echo "Detected root disk: /dev/$ROOT_DISK"

# 2. List all disk devices except root disk and swap disks
CANDIDATES=()
for dev in $(lsblk -d -n -o NAME,TYPE | awk '$2=="disk" {print $1}'); do
    if [ "$dev" = "$ROOT_DISK" ]; then
        continue
    fi
    IS_SWAP=$(lsblk -n -o FSTYPE "/dev/$dev" | tr -d ' ' || true)
    if [ "$IS_SWAP" = "swap" ] || grep -q "/dev/$dev" /proc/swaps 2>/dev/null; then
        echo "Skipping swap disk: /dev/$dev"
        continue
    fi
    CANDIDATES+=("/dev/$dev")
done

echo "Found ${#CANDIDATES[@]} candidate disk(s): ${CANDIDATES[*]}"

# 3. Validation gates
if [ ${#CANDIDATES[@]} -eq 0 ]; then
    echo "[-] ERROR: No unattached candidate disks found. Please attach the Linode volume first."
    exit 1
fi

if [ ${#CANDIDATES[@]} -gt 1 ]; then
    echo "[-] ERROR: More than one candidate disk found: ${CANDIDATES[*]}. Refusing to proceed for safety."
    exit 1
fi

TARGET_DEV=${CANDIDATES[0]}
echo "[+] Safely identified target block device: $TARGET_DEV"

# 4. Require explicit execution flag
if [ "$EXECUTE_FLAG" != "--execute" ]; then
    echo "[*] Dry run completed. To format, mount, and configure this device, rerun with:"
    echo "    $0 --execute"
    exit 0
fi

echo "[*] Commencing layout and formatting..."

# Verify size is exactly 100G
SIZE=$(lsblk -d -n -o SIZE "$TARGET_DEV" | tr -d ' ')
echo "Target device size: $SIZE"
if [ "$SIZE" != "100G" ] && [ "$SIZE" != "100.0G" ] && [ "$SIZE" != "100GB" ]; then
    echo "[-] ERROR: Candidate size is $SIZE, not exactly 100G. Aborting."
    exit 1
fi

# Abort immediately if device has acquired a filesystem, label, UUID, or partition
FSTYPE=$(blkid -o value -s TYPE "$TARGET_DEV" || true)
LABEL=$(blkid -o value -s LABEL "$TARGET_DEV" || true)
UUID_CHECK=$(blkid -o value -s UUID "$TARGET_DEV" || true)
HAS_PARTS=$(lsblk -n -o NAME "$TARGET_DEV" | wc -l | tr -d ' ')

if [ -n "$FSTYPE" ] || [ -n "$LABEL" ] || [ -n "$UUID_CHECK" ] || [ "$HAS_PARTS" -gt 1 ]; then
    echo "[-] ERROR: Device $TARGET_DEV has pre-existing filesystem ($FSTYPE), label ($LABEL), UUID ($UUID_CHECK), or partitions. Aborting."
    exit 1
fi

echo "[*] No filesystem detected. Formatting $TARGET_DEV as ext4 with label 'helm-data'..."
mkfs.ext4 -L helm-data "$TARGET_DEV"

# 6. Assign stable filesystem label
# Ensure label is helm-data
e2label "$TARGET_DEV" helm-data

# Get UUID
UUID=$(blkid -s UUID -o value "$TARGET_DEV")
echo "[+] Disk UUID: $UUID"

# 7. Mount at /var/lib/helm
MOUNT_POINT="/var/lib/helm"
mkdir -p "$MOUNT_POINT"

# Check if already mounted
if mountpoint -q "$MOUNT_POINT"; then
    echo "[!] Warning: $MOUNT_POINT is already mounted."
else
    echo "[*] Mounting $TARGET_DEV to $MOUNT_POINT..."
    mount "$TARGET_DEV" "$MOUNT_POINT"
fi

# 8. Add to /etc/fstab if not present
FSTAB_LINE="UUID=$UUID $MOUNT_POINT ext4 defaults,noatime,nofail 0 2"
cp /etc/fstab /etc/fstab.bak
if grep -q "$UUID" /etc/fstab; then
    echo "[!] fstab entry for $UUID already exists."
elif grep -q "$MOUNT_POINT" /etc/fstab; then
    echo "[-] ERROR: Another device is configured for $MOUNT_POINT in /etc/fstab. Please clean up."
    exit 1
else
    echo "[*] Adding entry to /etc/fstab..."
    echo "$FSTAB_LINE" >> /etc/fstab
fi

# 9. Verify remount
echo "[*] Verifying remount capability..."
umount "$MOUNT_POINT"
mount -a
if mountpoint -q "$MOUNT_POINT"; then
    echo "[+] Remount verification PASSED."
else
    echo "[-] ERROR: Failed to mount $MOUNT_POINT via mount -a."
    exit 1
fi

# 10. Create subdirectories
echo "[*] Creating subdirectories under $MOUNT_POINT..."
for dir in postgres evidence backups runtime jspace; do
    mkdir -p "$MOUNT_POINT/$dir"
done

# 11. Set ownership and permissions
echo "[*] Configuring permissions..."
chown -R root:root "$MOUNT_POINT"
chmod 755 "$MOUNT_POINT"
chmod 777 "$MOUNT_POINT/postgres"
chmod 700 "$MOUNT_POINT/evidence" "$MOUNT_POINT/backups" "$MOUNT_POINT/runtime" "$MOUNT_POINT/jspace"

# 12. Emit JSON validation report
CAPACITY=$(df -B1 "$MOUNT_POINT" | tail -n 1 | awk '{print $2}')
AVAILABLE=$(df -B1 "$MOUNT_POINT" | tail -n 1 | awk '{print $4}')

cat <<EOF > /tmp/volume_configuration.json
{
  "device": "$TARGET_DEV",
  "filesystem_uuid": "$UUID",
  "mount_point": "$MOUNT_POINT",
  "capacity_bytes": $CAPACITY,
  "available_bytes": $AVAILABLE,
  "fstab_entry_persisted": true,
  "verification_status": "OK",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
echo "[+] Configuration completed successfully."
cat /tmp/volume_configuration.json
