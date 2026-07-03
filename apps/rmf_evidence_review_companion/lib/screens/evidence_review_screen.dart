import 'package:flutter/material.dart';

class EvidenceReviewScreen extends StatelessWidget {
  const EvidenceReviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Evidence Review Prep')),
      body: const Center(child: Text('Prepare compliance evidence packages')),
    );
  }
}
