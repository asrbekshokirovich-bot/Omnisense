import 'dart:convert';
import 'package:http/http.dart' as http;

/// Thin client for the Omnisense Phase-0 API.
/// Point [baseUrl] at your backend (Android emulator: http://10.0.2.2:8000).
class OmniApi {
  OmniApi(this.baseUrl);
  final String baseUrl;

  Future<Map<String, dynamic>> health() async =>
      _get('/health');

  Future<Map<String, dynamic>> ingestText(String text, String lang) async =>
      _post('/ingest/text', {'text': text, 'lang': lang});

  Future<Map<String, dynamic>> ask(String question, String lang) async =>
      _post('/ask', {'question': question, 'lang': lang});

  Future<Map<String, dynamic>> briefing(String lang) async =>
      _get('/briefing?lang=$lang');

  Future<Map<String, dynamic>> deleteAll() async {
    final r = await http.delete(Uri.parse('$baseUrl/data'));
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    final r = await http.post(Uri.parse('$baseUrl$path'),
        headers: {'Content-Type': 'application/json'}, body: jsonEncode(body));
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final r = await http.get(Uri.parse('$baseUrl$path'));
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
