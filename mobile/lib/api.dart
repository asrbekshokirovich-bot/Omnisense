import 'dart:convert';
import 'package:http/http.dart' as http;

/// Thin client for the Omnisense Phase-0 API.
/// Point [baseUrl] at your backend (Android emulator: http://10.0.2.2:8000).
///
/// Pass [tenantId] to scope every call to a per-install identity (X-User-Id) so
/// two installs of the app on the same backend get separate memories.
class OmniApi {
  OmniApi(this.baseUrl, {this.tenantId});
  final String baseUrl;
  final String? tenantId;

  Map<String, String> _headers({String? contentType}) {
    final h = <String, String>{};
    if (contentType != null) h['Content-Type'] = contentType;
    final tid = tenantId;
    if (tid != null && tid.isNotEmpty) h['X-User-Id'] = tid;
    return h;
  }

  Future<Map<String, dynamic>> health() async => _get('/health');

  Future<Map<String, dynamic>> ingestText(String text, String lang) async =>
      _post('/ingest/text', {'text': text, 'lang': lang});

  /// Upload a recorded audio file to the STT pipeline (POST /ingest/audio, multipart).
  Future<Map<String, dynamic>> uploadAudio(String filePath, String lang) async {
    final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/ingest/audio'))
      ..fields['lang'] = lang
      ..files.add(await http.MultipartFile.fromPath('file', filePath));
    final tid = tenantId;
    if (tid != null && tid.isNotEmpty) req.headers['X-User-Id'] = tid;
    final resp = await req.send();
    final body = await resp.stream.bytesToString();
    return jsonDecode(body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> ask(String question, String lang) async =>
      _post('/ask', {'question': question, 'lang': lang});

  Future<Map<String, dynamic>> briefing(String lang) async => _get('/briefing?lang=$lang');

  Future<Map<String, dynamic>> usage() async => _get('/usage');

  /// Record a consent grant or revoke for the caller's tenant. Best-effort: failures
  /// are swallowed by the mobile layer so the on-device consent file stays the source
  /// of truth even when the backend is unreachable.
  Future<Map<String, dynamic>> recordConsent(String scope, bool granted, {String? reason}) async =>
      _post('/consent/$scope', {
        'granted': granted,
        if (reason != null) 'reason': reason,
      });

  Future<Map<String, dynamic>> deleteAll() async {
    final r = await http.delete(Uri.parse('$baseUrl/data'), headers: _headers());
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final r = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: _headers(contentType: 'application/json'),
      body: jsonEncode(body),
    );
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final r = await http.get(Uri.parse('$baseUrl$path'), headers: _headers());
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
