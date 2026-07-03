import 'package:flutter/material.dart';

class RmfChecklistScreen extends StatelessWidget {
  const RmfChecklistScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('RMF Checklist')),
      body: const Center(child: Text('NIST SP 800-53 checklists')),
    );
  }
}
