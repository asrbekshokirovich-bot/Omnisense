import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';

/// Per-install tenant identity for the Phase-0 X-User-Id header.
///
/// Generated once on first launch (random 16-byte hex), then read from a small file
/// under the app's documents directory. NOT real auth — that arrives with Telegram
/// OAuth + Payme/Click. But it lets the backend's tenant isolation (see
/// backend/app/main.py / app/usage.py) actually do something: two installs of the
/// app talking to the same backend get separate memories, counters, and owner
/// enrollments.
///
/// Wiping the file (Settings → "Forget this device") resets the tenant id so the
/// install starts cold — pairs with the backend's DELETE /data for full one-tap
/// privacy.
class TenantIdentity {
  TenantIdentity._(this.id);
  final String id;

  static const _filename = 'omni_tenant.txt';
  static Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/$_filename');
  }

  static Future<TenantIdentity> load() async {
    final f = await _file();
    if (await f.exists()) {
      final id = (await f.readAsString()).trim();
      if (id.isNotEmpty) return TenantIdentity._(id);
    }
    final fresh = _generate();
    await f.writeAsString(fresh, flush: true);
    return TenantIdentity._(fresh);
  }

  static Future<void> reset() async {
    final f = await _file();
    if (await f.exists()) {
      await f.delete();
    }
  }

  static String _generate() {
    final rng = Random.secure();
    final bytes = List<int>.generate(16, (_) => rng.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
