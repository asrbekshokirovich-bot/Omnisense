import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'api.dart';

/// Capture screen: record a conversation (default-OFF — recording only starts when the user
/// taps), then upload it to the STT pipeline. A text-paste fallback is included for quick
/// tests and for the offline mock STT. Background capture + BLE pendant land in Phase 1.
class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key, required this.api, required this.lang});
  final OmniApi api;
  final String lang;

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  final _recorder = AudioRecorder();
  final _text = TextEditingController();
  bool _recording = false;
  String _status = '';

  Future<void> _toggleRecord() async {
    if (_recording) {
      final path = await _recorder.stop();
      setState(() => _recording = false);
      if (path == null) return;
      setState(() => _status = 'Uploading…');
      final r = await widget.api.uploadAudio(path, widget.lang);
      setState(() => _status = 'Saved ${r['segments'] ?? '?'} memories.');
      return;
    }
    if (!await _recorder.hasPermission()) {
      setState(() => _status = 'Microphone permission denied.');
      return;
    }
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/omni_${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _recorder.start(const RecordConfig(), path: path);
    setState(() {
      _recording = true;
      _status = 'Recording… tap to stop.';
    });
  }

  Future<void> _ingestText() async {
    if (_text.text.trim().isEmpty) return;
    final r = await widget.api.ingestText(_text.text, widget.lang);
    setState(() => _status = 'Saved ${r['segments'] ?? '?'} memories.');
    _text.clear();
  }

  @override
  void dispose() {
    _recorder.dispose();
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (_recording) const _RecordingIndicator(),
        Center(
          child: FilledButton.icon(
            onPressed: _toggleRecord,
            icon: Icon(_recording ? Icons.stop : Icons.mic),
            label: Text(_recording ? 'Stop & save' : 'Record a conversation'),
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Capture is default-off. Recording only runs while this screen is open and only '
          'after you tap above.',
          style: TextStyle(color: Colors.black54, fontSize: 12),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        const Divider(),
        const Text('…or paste a transcript', style: TextStyle(color: Colors.black54)),
        const SizedBox(height: 8),
        TextField(
          controller: _text,
          maxLines: 4,
          decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'Transcript…'),
        ),
        const SizedBox(height: 8),
        OutlinedButton(onPressed: _ingestText, child: const Text('Remember text')),
        const SizedBox(height: 16),
        Text(_status, style: const TextStyle(fontWeight: FontWeight.w600)),
      ]),
    );
  }
}

/// Pulsing red dot + "Recording" label, shown ONLY while audio capture is active.
/// Designed to be impossible to miss — meeting the "visible recording indicator"
/// commitment from the consent screen and the privacy law's spirit.
class _RecordingIndicator extends StatefulWidget {
  const _RecordingIndicator();
  @override
  State<_RecordingIndicator> createState() => _RecordingIndicatorState();
}

class _RecordingIndicatorState extends State<_RecordingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(seconds: 1))..repeat(reverse: true);
  late final Animation<double> _a = Tween(begin: 0.4, end: 1.0).animate(_c);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.red.withOpacity(0.08),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.red.withOpacity(0.4)),
          ),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            FadeTransition(
              opacity: _a,
              child: const Icon(Icons.fiber_manual_record, color: Colors.red, size: 14),
            ),
            const SizedBox(width: 8),
            const Text('Recording — tap "Stop & save" to end.',
                style: TextStyle(color: Colors.red, fontWeight: FontWeight.w600)),
          ]),
        ),
      );
}
