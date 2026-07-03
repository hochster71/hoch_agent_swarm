import 'package:flutter_test/flutter_test.dart';
import 'package:rmf_evidence_review_companion/app.dart';

void main() {
  testWidgets('App renders dashboard main header', (WidgetTester tester) async {
    await tester.pumpWidget(const RmfCompanionApp());
    expect(find.text('RMF Companion Dashboard'), findsOneWidget);
  });
}
