import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

class RmfCompanionApp extends StatelessWidget {
  const RmfCompanionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RMF Evidence Review Companion',
      theme: ThemeData.dark(),
      home: const HomeScreen(),
    );
  }
}
