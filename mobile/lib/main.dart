import 'package:flutter/material.dart';
import 'api.dart';
import 'capture.dart';

// Phase-0 shell: three screens (Capture / Ask / Briefing) over the backend API.
// Real on-device recording + BLE pendant capture come in Phase 1; here "Capture" ingests
// typed/pasted text as a stand-in so the full loop is demonstrable.

const String kApiBase = String.fromEnvironment('OMNI_API', defaultValue: 'http://10.0.2.2:8000');

void main() => runApp(const OmniApp());

class OmniApp extends StatelessWidget {
  const OmniApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Omnisense',
        theme: ThemeData(colorSchemeSeed: const Color(0xFF6366F1), useMaterial3: true),
        home: const Home(),
      );
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  final api = OmniApi(kApiBase);
  int _tab = 0;
  String _lang = 'ru';

  final _question = TextEditingController();
  String _askOut = '';
  String _briefOut = '';

  Future<void> _ask() async {
    final r = await api.ask(_question.text, _lang);
    final cites = (r['citations'] as List?) ?? [];
    final c = cites.isNotEmpty ? '\n\n↳ ${cites.first['timestamp']} ${cites.first['speaker']}: ${cites.first['text']}' : '';
    setState(() => _askOut = '${r['answer']}$c');
  }

  Future<void> _brief() async {
    final r = await api.briefing(_lang);
    final items = ((r['action_items'] as List?) ?? []).join('\n• ');
    setState(() => _briefOut = '${r['summary']}\n\nAction items:\n• $items');
  }

  @override
  Widget build(BuildContext context) {
    final bodies = [
      CaptureScreen(api: api, lang: _lang),
      _pane('Ask your memory', _question, 'e.g. when is the demo?', _ask, 'Ask', _askOut),
      Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          FilledButton(onPressed: _brief, child: const Text('Generate morning briefing')),
          const SizedBox(height: 12),
          Text(_briefOut),
        ]),
      ),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Omnisense'), actions: [
        DropdownButton<String>(
          value: _lang,
          underline: const SizedBox(),
          items: const [
            DropdownMenuItem(value: 'ru', child: Text('RU')),
            DropdownMenuItem(value: 'uz', child: Text('UZ')),
            DropdownMenuItem(value: 'en', child: Text('EN')),
          ],
          onChanged: (v) => setState(() => _lang = v ?? 'ru'),
        ),
        const SizedBox(width: 12),
      ]),
      body: bodies[_tab],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.mic), label: 'Capture'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Ask'),
          NavigationDestination(icon: Icon(Icons.summarize), label: 'Briefing'),
        ],
      ),
    );
  }

  Widget _pane(String title, TextEditingController ctrl, String hint, VoidCallback onTap, String btn, String out) =>
      Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          TextField(controller: ctrl, maxLines: title.startsWith('Capture') ? 5 : 1,
              decoration: InputDecoration(hintText: hint, border: const OutlineInputBorder())),
          const SizedBox(height: 10),
          FilledButton(onPressed: onTap, child: Text(btn)),
          const SizedBox(height: 12),
          Text(out),
        ]),
      );
}
