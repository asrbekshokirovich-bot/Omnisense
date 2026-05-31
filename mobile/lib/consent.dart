import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

/// First-launch consent screen. The product's whole pitch is "your voice stays in
/// Uzbekistan and never leaves without your tap"; the app cannot do anything before
/// the user explicitly agrees to that.
///
/// Persistence is a tiny file (`omni_consent.json`) — wiping it (Settings → revoke
/// consent) re-prompts the user. We deliberately do NOT bundle this in shared_prefs
/// to keep the on-disk surface trivially auditable.
class ConsentRecord {
  ConsentRecord({required this.recording, required this.crossBorderLLM, required this.grantedAt});
  final bool recording;
  final bool crossBorderLLM;
  final DateTime grantedAt;

  Map<String, dynamic> toJson() => {
        'recording': recording,
        'crossBorderLLM': crossBorderLLM,
        'grantedAt': grantedAt.toIso8601String(),
      };
  static ConsentRecord fromJson(Map<String, dynamic> j) => ConsentRecord(
        recording: j['recording'] == true,
        crossBorderLLM: j['crossBorderLLM'] == true,
        grantedAt: DateTime.tryParse(j['grantedAt'] as String? ?? '') ?? DateTime.now(),
      );
}

class ConsentStore {
  static const _filename = 'omni_consent.json';
  static Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/$_filename');
  }

  static Future<ConsentRecord?> load() async {
    final f = await _file();
    if (!await f.exists()) return null;
    try {
      final raw = await f.readAsString();
      return ConsentRecord.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  static Future<void> save(ConsentRecord r) async {
    final f = await _file();
    await f.writeAsString(jsonEncode(r.toJson()), flush: true);
  }

  static Future<void> clear() async {
    final f = await _file();
    if (await f.exists()) await f.delete();
  }
}

/// A blocking gate: shows the consent screen until the user accepts; then renders [child].
class ConsentGate extends StatefulWidget {
  const ConsentGate({super.key, required this.child});
  final Widget child;
  @override
  State<ConsentGate> createState() => _ConsentGateState();
}

class _ConsentGateState extends State<ConsentGate> {
  ConsentRecord? _record;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    ConsentStore.load().then((r) => setState(() {
          _record = r;
          _loading = false;
        }));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_record?.recording == true) return widget.child;
    return _ConsentScreen(onAccept: (allowCrossBorder) async {
      final r = ConsentRecord(
        recording: true,
        crossBorderLLM: allowCrossBorder,
        grantedAt: DateTime.now(),
      );
      await ConsentStore.save(r);
      if (mounted) setState(() => _record = r);
    });
  }
}

class _ConsentScreen extends StatefulWidget {
  const _ConsentScreen({required this.onAccept});
  final Future<void> Function(bool allowCrossBorderLLM) onAccept;
  @override
  State<_ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<_ConsentScreen> {
  bool _allowCrossBorder = false;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Omnisense — your privacy')),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: ListView(children: [
              const Text('Before you start',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 16),
              const _Bullet('Capture is default-off. The app records only when you tap '
                  '"Record" — there is no automatic, always-on recording.'),
              const _Bullet('Your voice and voiceprints stay in Uzbekistan. The audio is '
                  'transcribed and stored in-country.'),
              const _Bullet('One tap deletes everything. Settings → "Delete my memory" '
                  'wipes your transcripts, voiceprint, and counters.'),
              const _Bullet('Recording other people requires their consent. By using this '
                  'app you confirm you have permission.'),
              const SizedBox(height: 16),
              SwitchListTile(
                title: const Text('Allow text excerpts to be sent abroad for AI answers'),
                subtitle: const Text(
                    'Only derived TEXT (never your voice) is sent to a cross-border LLM '
                    'for answers and briefings. You can turn this off later.'),
                value: _allowCrossBorder,
                onChanged: (v) => setState(() => _allowCrossBorder = v),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => widget.onAccept(_allowCrossBorder),
                child: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text('I understand — continue'),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'You can review or revoke consent any time from Settings.',
                style: TextStyle(color: Colors.black54),
              ),
            ]),
          ),
        ),
      );
}

class _Bullet extends StatelessWidget {
  const _Bullet(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Padding(padding: EdgeInsets.only(top: 6, right: 8), child: Icon(Icons.check_circle_outline, size: 18)),
          Expanded(child: Text(text)),
        ]),
      );
}
