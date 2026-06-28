import type { Asset } from "./assetTypes";

export const getSelectedAsset = (assets: Asset[], selectedAssetId: string | null): Asset | null => {
  if (!selectedAssetId) return null;
  return assets.find(a => a.id === selectedAssetId) || null;
};
