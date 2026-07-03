import 'package:flutter/material.dart';

class PoamPrepScreen extends StatelessWidget {
  const PoamPrepScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('POA&M Prep')),
      body: const Center(child: Text('Prepare Plan of Action & Milestones')),
    );
  }
}
