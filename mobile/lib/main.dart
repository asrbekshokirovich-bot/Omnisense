import 'package:flutter/material.dart';

import 'api.dart';
import 'capture.dart';
import 'consent.dart';
import 'tenant.dart';

// Phase-0 shell: four screens (Capture / Ask / Briefing / Settings) over the backend API.
// Real on-device background recording + BLE pendant capture come in Phase 1; the
// background-capture plan lives at docs/mobile-background-capture.md.

const String kApiBase = String.fromEnvironment('OMNI_API', defaultValue: 'http://10.0.2.2:8000');

void main() => runApp(const OmniApp());

class OmniApp extends StatelessWidget {
  const OmniApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Omnisense',
        theme: ThemeData(colorSchemeSeed: const Color(0xFF6366F1), useMaterial3: true),
        home: const ConsentGate(child: Home()),
      );
}

class Home extends StatefulWidget {
  const Home({super.key});
  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  OmniApi? api;
  int _tab = 0;
  String _lang = 'ru';

  final _question = TextEditingController();
  String _askOut = '';
  String _briefOut = '';

  @override
  void initState() {
    super.initState();
    _loadIdentity();
  }

  Future<void> _loadIdentity() async {
    final t = await TenantIdentity.load();
    if (!mounted) return;
    setState(() => api = OmniApi(kApiBase, tenantId: t.id));
  }

  Future<void> _ask() async {
    if (api == null) return;
    final r = await api!.ask(_question.text, _lang);
    final cites = (r['citations'] as List?) ?? [];
    final c = cites.isNotEmpty
        ? '\n\n↳ ${cites.first['timestamp']} ${cites.first['speaker']}: ${cites.first['text']}'
        : '';
    setState(() => _askOut = '${r['answer']}$c');
  }

  Future<void> _brief() async {
    if (api == null) return;
    final r = await api!.briefing(_lang);
    final items = ((r['action_items'] as List?) ?? []).join('\n• ');
    setState(() => _briefOut = '${r['summary']}\n\nAction items:\n• $items');
  }

  @override
  Widget build(BuildContext context) {
    if (api == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final bodies = [
      CaptureScreen(api: api!, lang: _lang),
      _pane('Ask your memory', _question, 'e.g. when is the demo?', _ask, 'Ask', _askOut),
      Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          FilledButton(onPressed: _brief, child: const Text('Generate morning briefing')),
          const SizedBox(height: 12),
          Text(_briefOut),
        ]),
      ),
      _SettingsScreen(api: api!),
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
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }

  Widget _pane(String title, TextEditingController ctrl, String hint, VoidCallback onTap,
      String btn, String out) =>
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

/// Settings: per-install tenant id, usage counters, one-tap delete-all, revoke consent.
class _SettingsScreen extends StatefulWidget {
  const _SettingsScreen({required this.api});
  final OmniApi api;
  @override
  State<_SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<_SettingsScreen> {
  Map<String, dynamic>? _usage;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      final u = await widget.api.usage();
      if (mounted) setState(() => _usage = u);
    } catch (_) {/* offline — show what we have */}
  }

  Future<void> _wipe() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete all your memory?'),
        content: const Text(
            'This wipes every segment, session, voiceprint, and usage counter on the '
            'server for THIS install. Cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton.tonal(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete everything'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    final r = await widget.api.deleteAll();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Deleted ${r['deleted_segments'] ?? '?'} memories.')),
    );
    _refresh();
  }

  Future<void> _forgetDevice() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Forget this device?'),
        content: const Text(
            'Resets your per-install identity. After this, the app gets a fresh tenant '
            'id and the server treats this install as a new user. Existing memory on the '
            'server is NOT deleted by this — use "Delete my memory" first if you also '
            'want to wipe it.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton.tonal(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Forget'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await TenantIdentity.reset();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Device identity cleared. Restart the app.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Privacy & data',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      const SizedBox(height: 12),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Tenant: ${widget.api.tenantId ?? '(none)'}',
                style: const TextStyle(fontFamily: 'monospace')),
            const SizedBox(height: 6),
            if (_usage != null) ...[
              Text('Segments ingested: ${_usage!['segments_ingested']}'),
              Text('Questions asked:   ${_usage!['questions_asked']}'),
              Text('Briefings made:    ${_usage!['briefings_generated']}'),
            ] else
              const Text('(usage unavailable — backend offline?)',
                  style: TextStyle(color: Colors.black54)),
          ]),
        ),
      ),
      const SizedBox(height: 16),
      FilledButton.icon(
        onPressed: _wipe,
        icon: const Icon(Icons.delete_forever),
        label: const Text('Delete my memory'),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        onPressed: _forgetDevice,
        icon: const Icon(Icons.fingerprint),
        label: const Text('Forget this device'),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        onPressed: () async {
          await ConsentStore.clear();
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Consent revoked. Restart the app to re-onboard.')),
          );
        },
        icon: const Icon(Icons.lock_reset),
        label: const Text('Revoke consent & re-onboard'),
      ),
      const SizedBox(height: 24),
      const Text(
        'Your voice stays in Uzbekistan. Background recording is not yet enabled — '
        'capture only runs while the Capture screen is open and you have tapped Record.',
        style: TextStyle(color: Colors.black54),
      ),
    ]);
  }
}
