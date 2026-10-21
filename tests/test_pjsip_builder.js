'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {build} = require('../smartify_sip_manager/pjsip-builder.js');
const base = {extension:'107', displayName:'Beate Linphone', password:'test1234test1234'};

test('legacy defaults preserve AOR/auth/endpoint with configurable basics', () => {
 const r=build(base);
 for(const line of ['max_contacts=1','remove_existing=yes','remove_unavailable=no','qualify_frequency=0','context=default','disallow=all','allow=alaw,ulaw','direct_media=no','force_rport=yes','rewrite_contact=yes','rtp_symmetric=yes','callerid="Beate Linphone" <107>']) {
  assert.ok(r.snippet.includes(line+'\n'), line);
 }
 assert.equal((r.snippet.match(/^\[107\]$/mg)||[]).length,3);
 assert.ok(r.snippet.includes('password=test1234test1234'));
});

test('multiple devices and codec/nat/registrations customization', () => {
 const r=build({...base,maxContacts:'4', removeExisting:'no',removeUnavailable:'yes',qualifyFrequency:'30',
  authUsername:'beate-107', context:'intern',transport:'transport-tcp', minimumExpiration:'120',
  defaultExpiration:'2400',maximumExpiration:'3600',codecs:['g722','alaw','opus'],dtmfMode:'info',
  directMedia:'yes', forceRport:'no',rewriteContact:'no',rtpSymmetric:'no',iceSupport:'yes'});
 for(const field of ['max_contacts=4','remove_existing=no','remove_unavailable=yes','qualify_frequency=30',
 'username=beate-107','context=intern','transport=transport-tcp', 'allow=g722,alaw,opus',
 'minimum_expiration=120','default_expiration=2400','maximum_expiration=3600',
 'dtmf_mode=info','direct_media=yes','force_rport=no','rewrite_contact=no','rtp_symmetric=no','ice_support=yes']) {
  assert.ok(r.snippet.includes(field+'\n'),field);
 }
 assert.ok(r.notices.some(x=>x.includes('Opus')));
});

test('presets and warnings for replacing registrations', () => {
 assert.ok(build({...base,maxContacts:'3',removeExisting:'yes'}).notices.some(x=>x.includes('verdrängen')));
 assert.equal(build({...base,maxContacts:'3',removeExisting:'no'}).notices.some(x=>x.includes('verdrängen')),false);
});

test('diacritics in caller id', () => {
 assert.ok(build({...base,displayName:'Tür Süd - René'}).snippet.includes('callerid="Tür Süd - René" <107>'));
});

test('reject PJSIP settings injection and impossible ranges', () => {
 const invalid = [
  {extension:'107\n[evil]'}, {displayName:'X"\ncontext=external'}, {password:'xxx\nallow=all'},
  {password:'thisIsLong;comment'}, {password:'thisIsLong#comment'}, {maxContacts:'0'},
  {maxContacts:'2.3'}, {maxContacts:'99x'}, {maxContacts:'9999999999999999999999'},
  {removeExisting:'maybe'}, {context:'default\n[evil]'}, {transport:'udp\nendpoint=evil'},
  {codecs:[]},{codecs:['alaw','alaw']},{codecs:['all']},{dtmfMode:'invalid'},
  {minimumExpiration:'4000',defaultExpiration:'3600'},
  {defaultExpiration:'8000',maximumExpiration:'7200'},
  {rtpSymmetric:'no\nsecret=yes'},
 ];
 for(const bad of invalid) assert.throws(()=>build({...base,...bad}), /Ungültige PJSIP-Einstellung/,JSON.stringify(bad));
});
