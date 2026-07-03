import 'package:flutter/material.dart';

class ControlFamilyScreen extends StatelessWidget {
  const ControlFamilyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Control Families')),
      body: const Center(child: Text('NIST SP 800-53 families')),
    );
  }
}
