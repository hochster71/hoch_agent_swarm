import 'dart:convert';
import 'package:flutter/services.dart';

class OfflineDataService {
  Future<Map<String, dynamic>> loadAssetData(String assetName) async {
    try {
      final jsonString = await rootBundle.loadString('assets/data/$assetName.json');
      return json.decode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      return {};
    }
  }
}
