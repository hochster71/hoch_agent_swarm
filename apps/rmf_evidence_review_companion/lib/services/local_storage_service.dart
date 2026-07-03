class LocalStorageService {
  final Map<String, dynamic> _localMemory = {};

  Future<void> saveItem(String key, String value) async {
    _localMemory[key] = value;
  }

  Future<String?> readItem(String key) async {
    return _localMemory[key] as String?;
  }
}
