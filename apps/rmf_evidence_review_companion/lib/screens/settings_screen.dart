import 'package:flutter/material.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings & Disclaimer')),
      body: const Padding(
        padding: EdgeInsets.all(16.0),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Disclaimer',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 10),
              Text(
                'This RMF Evidence Review Companion is a standalone checklist utility meant to assist in RMF/compliance audit preparation. It is NOT an official assessment system, does NOT grant regulatory ATO compliance, and does NOT replace the expert review and cybersecurity engineering judgment of an ISSO, ISSM, SCA, or AO. Users remain solely responsible for system validations.',
                style: TextStyle(fontSize: 14),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
