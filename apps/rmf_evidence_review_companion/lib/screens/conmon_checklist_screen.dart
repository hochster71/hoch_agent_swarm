import 'package:flutter/material.dart';

class ConmonChecklistScreen extends StatelessWidget {
  const ConmonChecklistScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ConMon Checklist')),
      body: const Center(child: Text('Continuous Monitoring checklists')),
    );
  }
}
