/* Smartify SIP Manager · PJSIP-Konfigurationsgenerator v1.3.3
 * Nur reine Datentransformation: keine Datei- oder Netzwerkzugriffe.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SmartifyPjsip = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const CODECS = Object.freeze(['alaw', 'ulaw', 'g722', 'gsm', 'opus', 'g729']);
  const DTMF = Object.freeze(['rfc4733', 'inband', 'info', 'auto', 'auto_info']);
  const BOOL = Object.freeze(['yes', 'no']);

  function fail(label) { throw new Error('Ungültige PJSIP-Einstellung: ' + label); }
  function digits(value, label, low, high) {
    const s = String(value ?? '').trim();
    if (!/^\d+$/.test(s)) fail(label + ' (Zahl erforderlich)');
    const n = Number(s);
    if (!Number.isSafeInteger(n) || n < low || n > high) fail(label + ' (' + low + '–' + high + ')');
    return n;
  }
  function option(value, label, allowed) {
    if (!allowed.includes(value)) fail(label);
    return value;
  }
  function token(value, label, re, required = true) {
    const v = String(value ?? '').trim();
    if ((!v && required) || (v && !re.test(v))) fail(label);
    return v;
  }
  function build(input) {
    if (!input || typeof input !== 'object') fail('Eingaben');
    const ext = token(input.extension, 'Nebenstellennummer', /^\d{2,6}$/);
    const displayName = token(input.displayName, 'Anzeigename', /^[\p{L}\p{N} ._'-]{1,55}$/u);
    const password = String(input.password ?? '');
    // Semikolon startet in Asterisk-Kommentare; keine Zeilenumbrüche oder Sonderformatierungen.
    if (!(input.allowEmptyPassword && password==='') && (!/^[\x21-\x7E]{1,128}$/.test(password) || /[;#]/.test(password))) {
      fail('Passwort (1–128 ASCII-Zeichen, ohne Leerzeichen, ; oder #)');
    }
    const user = token(input.authUsername || ext, 'SIP-Anmeldename', /^[A-Za-z0-9_.+@-]{1,64}$/);
    const context = token(input.context || 'default', 'Dialplan-Kontext', /^[A-Za-z0-9_.-]{1,64}$/);
    const transport = token(input.transport || '', 'Transportname', /^[A-Za-z0-9_.-]{1,64}$/, false);
    const contacts = digits(input.maxContacts ?? 1, 'max_contacts', 1, 100);
    const existing = option(input.removeExisting ?? 'yes', 'remove_existing', BOOL);
    const unavailable = option(input.removeUnavailable ?? 'no', 'remove_unavailable', BOOL);
    const qualify = digits(input.qualifyFrequency ?? 0, 'qualify_frequency', 0, 3600);
    const minimum = digits(input.minimumExpiration ?? 60, 'minimum_expiration', 1, 86400);
    const normal = digits(input.defaultExpiration ?? 3600, 'default_expiration', 1, 86400);
    const maximum = digits(input.maximumExpiration ?? 7200, 'maximum_expiration', 1, 86400);
    if (minimum > normal || normal > maximum) fail('Registrierungszeiten: Minimum ≤ Standard ≤ Maximum');
    const codecs = input.codecs ?? ['alaw', 'ulaw'];
    if (!Array.isArray(codecs) || !codecs.length || codecs.some(x => !CODECS.includes(x)) || new Set(codecs).size !== codecs.length) fail('Codecs');
    const dtmf = option(input.dtmfMode ?? 'rfc4733', 'dtmf_mode', DTMF);
    const direct = option(input.directMedia ?? 'no', 'direct_media', BOOL);
    const rport = option(input.forceRport ?? 'yes', 'force_rport', BOOL);
    const rewrite = option(input.rewriteContact ?? 'yes', 'rewrite_contact', BOOL);
    const symmetric = option(input.rtpSymmetric ?? 'yes', 'rtp_symmetric', BOOL);
    const ice = option(input.iceSupport ?? 'no', 'ice_support', BOOL);
    const lines = [
      `; Smartify · Nebenstelle ${ext} · generiert, noch nicht aktiv`,
      '; Bestehende Definitionen und den wirksamen Dialplan vor Übernahme prüfen',
      `[${ext}]`, 'type=aor', `max_contacts=${contacts}`, `remove_existing=${existing}`,
      `remove_unavailable=${unavailable}`, `qualify_frequency=${qualify}`,
      `minimum_expiration=${minimum}`, `default_expiration=${normal}`, `maximum_expiration=${maximum}`,
      '', `[${ext}]`, 'type=auth', 'auth_type=userpass', `username=${user}`, `password=${password}`,
      '', `[${ext}]`, 'type=endpoint', `context=${context}`, `aors=${ext}`, `auth=${ext}`
    ];
    if (transport) lines.push(`transport=${transport}`);
    lines.push('disallow=all', `allow=${codecs.join(',')}`, `dtmf_mode=${dtmf}`, `direct_media=${direct}`,
      `force_rport=${rport}`, `rewrite_contact=${rewrite}`, `rtp_symmetric=${symmetric}`,
      `ice_support=${ice}`, `callerid="${displayName}" <${ext}>`);
    const notices = [];
    if (password && password.length < 12) notices.push('Kurzes SIP-Passwort: Bei externer Erreichbarkeit deutlich längeres, zufälliges Passwort empfohlen.');
    if (contacts > 1 && existing === 'yes') notices.push('remove_existing=yes kann bei Überschreiten von max_contacts eine bestehende Registrierung verdrängen.');
    if (user !== ext) notices.push('Abweichender SIP-Anmeldename: AOR und SIP-Identität des Clients passend konfigurieren.');
    if (transport) notices.push('Den Transport ' + transport + ' vorher in Asterisk mit „pjsip show transports“ prüfen.');
    if (codecs.includes('opus') || codecs.includes('g729')) notices.push('Opus/G.729 setzen ein installiertes und verfügbares Codec-Modul voraus.');
    if (direct === 'yes') notices.push('direct_media=yes erlaubt direkte RTP-Audioverbindungen und kann bei NAT/Türstationen Probleme verursachen.');
    return { snippet: lines.join('\n') + '\n', notices, extension: ext };
  }
  return { build, CODECS, DTMF };
});
