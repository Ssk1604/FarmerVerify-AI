// chatbot/chat.js — FarmerVerify AI Guided Chatbot
'use strict';

// ── Config ───────────────────────────────────────────────────────────────────
const CONFIG = {
  API_BASE:              'http://localhost:8000',
  INACTIVITY_TIMEOUT_MS: 3 * 60 * 1000,
  RESUME_TIMEOUT_MS:     10 * 60 * 1000,
  MAX_FILE_SIZE_MB:      10,
  ALLOWED_TYPES:         ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'],
  ALLOWED_PDF_TYPE:      'application/pdf',
  BOT_DELAY_MS:          800,
};

// ── Strings ───────────────────────────────────────────────────────────────────
const STRINGS = {
  en: {
    lang_prompt:     '🌳 Welcome to **FarmerVerify AI**!\n\nPlease choose your language:\n\n_(You can also type: english, hindi, or marathi)_',
    doc_prompt:      'Please select the type of document you want to verify:\n\n_(You can also type the document name, or type **check status**)_',
    pdf_detected:   '📄 PDF detected! I will process each page separately and verify all documents automatically. This may take a moment...',
    pdf_processing: '⏳ Processing PDF page {page} of {total}...',
    pdf_complete:   '✅ PDF processed! {total} documents analysed — {verified} verified, {review} need review, {rejected} rejected.',
    upload_prompt: {
      land_record:   '🏞️ Please take a clear photo of your **Land Record (7/12 extract)** and upload it.\n\n📌 Tips:\n• Full page must be visible\n• Use good lighting\n• Hold phone steady',
      bank_passbook: '🏦 Please take a clear photo of the **first page** of your **Bank Passbook**.\n\n📌 Tips:\n• Name, account number, and IFSC must be visible\n• Avoid shadows',
      aadhaar_card:  '🆔 Please take a clear photo of your **Aadhaar Card** (front side).\n\n📌 Tips:\n• Name and 12-digit number must be visible\n• Avoid covering corners',
      voter_id:      '🗳️ Please take a clear photo of your **Voter ID** (front side).\n\n📌 Tips:\n• Full name and photo must be clearly visible',
    },
    uploading:       '⏳ Uploading your document…',
    quality_check:   '🔍 Checking image quality…',
    ocr_running:     '📖 Reading document with AI…',
    extracting:      '🔎 Extracting key fields…',
    matching:        '🔗 Matching with farmer records…',
    fraud_check:     '🛡️ Running fraud detection…',
    done:            '✅ Verification complete!',
    upload_another:  'Would you like to upload another document?',
    yes:             'Yes, upload another',
    no:              "No, I'm done",
    goodbye:         '👋 Thank you for using FarmerVerify AI. Session ended.',
    upload_error:    '❌ Something went wrong. Please try again.',
    file_too_large:  '⚠️ File too large (max 10MB). Please compress and retry.',
    invalid_type:    '⚠️ Only JPG, PNG, or WEBP images are supported.',
    inactivity:      'Session paused due to inactivity.',
    inactivity_warn: '⚠️ Still there? Session will pause in 1 minute.',
    resume:          'Resume Session',
    session_expired: 'Session expired. Click **Restart** to begin again.',
    status_ask_id:   '🔍 Enter your **Reference ID** to check status:\n\n_(Looks like: `a1b2c3d4e5f6`)_',
    status_checking: '⏳ Looking up your document…',
    status_not_found:'❌ No document found with that Reference ID.',
    status_error:    '❌ Could not check status. Please try again.',
    check_status:    '🔍 Check Status',
    retry_prompt:    'What would you like to do?',
    try_again:       '🔄 Try Again',
    change_doc:      '🔀 Different Document',
    cancel:          '✖ Cancel',
    type_hint_lang:  'Please type **english**, **hindi**, or **marathi**.',
    type_hint_doc:   'Please type a document name like **aadhaar**, **passbook**, **land record**, or **voter id**.',
    type_hint_upload:'📎 Use the attach button (📎) to upload your document.\n\nOr type **check status**.',
    type_hint_ref:   'That does not look like a Reference ID. Try a 12-character code.',
    switched_doc:    'Switched to **{doc}**. Please upload your document.',
    doc_types: {
      land_record:   '🏞️ Land Record',
      bank_passbook: '🏦 Bank Passbook',
      aadhaar_card:  '🆔 Aadhaar Card',
      voter_id:      '🗳️ Voter ID',
    },
  },
  hi: {
    lang_prompt:     '🌳 **FarmerVerify AI** में स्वागत है!\n\nभाषा चुनें:\n\n_(आप टाइप भी कर सकते हैं: english, hindi, marathi)_',
    doc_prompt:      'दस्तावेज़ का प्रकार चुनें:\n\n_(नाम टाइप करें या **स्थिति जाँचें** टाइप करें)_',
    pdf_detected:   '📄 PDF मिला! मैं हर पेज अलग से जाँचूँगा। इसमें थोड़ा समय लग सकता है...',
    pdf_processing: '⏳ PDF पेज {page}/{total} प्रोसेस हो रहा है...',
    pdf_complete:   '✅ PDF प्रोसेस हुई! {total} दस्तावेज़ — {verified} सत्यापित, {review} समीक्षाधीन, {rejected} अस्वीकृत.',
    upload_prompt: {
      land_record:   '🏞️ **जमीन रिकॉर्ड (7/12 उतारा)** की स्पष्ट फोटो अपलोड करें।',
      bank_passbook: '🏦 **बैंक पासबुक** के पहले पेज की स्पष्ट फोटो अपलोड करें।',
      aadhaar_card:  '🆔 **आधार कार्ड** (सामने की तरफ) की स्पष्ट फोटो अपलोड करें।',
      voter_id:      '🗳️ **मतदाता पहचान पत्र** (सामने की तरफ) की स्पष्ट फोटो अपलोड करें।',
    },
    uploading:       '⏳ दस्तावेज़ अपलोड हो रहा है…',
    quality_check:   '🔍 छवि गुणवत्ता जाँच…',
    ocr_running:     '📖 AI से दस्तावेज़ पढ़ रहे हैं…',
    extracting:      '🔎 जानकारी निकाल रहे हैं…',
    matching:        '🔗 किसान रिकॉर्ड से मिला रहे हैं…',
    fraud_check:     '🛡️ जाँच कर रहे हैं…',
    done:            '✅ सत्यापन पूर्ण!',
    upload_another:  'क्या आप और दस्तावेज़ अपलोड करना चाहते हैं?',
    yes:             'हाँ, और अपलोड करें',
    no:              'नहीं, बस',
    goodbye:         '👋 धन्यवाद। सत्र समाप्त।',
    upload_error:    '❌ कुछ गलत हुआ। पुनः प्रयास करें।',
    file_too_large:  '⚠️ फ़ाइल बहुत बड़ी है।',
    invalid_type:    '⚠️ केवल JPG, PNG या WEBP समर्थित।',
    inactivity:      'सत्र रोका गया।',
    inactivity_warn: '⚠️ 1 मिनट में सत्र रुकेगा।',
    resume:          'जारी रखें',
    session_expired: 'सत्र समाप्त। **Restart** पर क्लिक करें।',
    status_ask_id:   '🔍 **संदर्भ ID** दर्ज करें।',
    status_checking: '⏳ खोज रहे हैं…',
    status_not_found:'❌ दस्तावेज़ नहीं मिला।',
    status_error:    '❌ स्थिति जाँच विफल।',
    check_status:    '🔍 स्थिति जाँचें',
    retry_prompt:    'आप क्या करना चाहते हैं?',
    try_again:       '🔄 फिर से प्रयास',
    change_doc:      '🔀 अलग दस्तावेज़',
    cancel:          '✖ रद्द',
    type_hint_lang:  '**english**, **hindi**, या **marathi** टाइप करें।',
    type_hint_doc:   'दस्तावेज़ का नाम टाइप करें।',
    type_hint_upload:'📎 अटैच बटन से दस्तावेज़ अपलोड करें।',
    type_hint_ref:   'यह संदर्भ ID जैसा नहीं दिखता।',
    switched_doc:    '**{doc}** चुना गया।',
    doc_types: {
      land_record:   '🏞️ जमीन रिकॉर्ड',
      bank_passbook: '🏦 बैंक पासबुक',
      aadhaar_card:  '🆔 आधार कार्ड',
      voter_id:      '🗳️ मतदाता पहचान पत्र',
    },
  },
  mr: {
    lang_prompt:     '🌳 **FarmerVerify AI** मध्ये स्वागत!\n\nभाषा निवडा:\n\n_(टाइप करा: english, hindi, marathi)_',
    doc_prompt:      'दस्तऐवजाचा प्रकार निवडा:\n\n_(नाव टाइप करा किंवा **स्थिती तपासा**)_',
     pdf_detected:   '📄 PDF सापडला! मी प्रत्येक पान स्वतंत्रपणे तपासेन. यास थोडा वेळ लागू शकतो...',
    pdf_processing: '⏳ PDF पान {page}/{total} प्रक्रिया होत आहे...',
    pdf_complete:   '✅ PDF प्रक्रिया पूर्ण! {total} दस्तऐवज — {verified} सत्यापित, {review} पुनरावलोकन, {rejected} नाकारले.',
    upload_prompt: {
      land_record:   '🏞️ **जमीन उतारा (7/12)** चा स्पष्ट फोटो अपलोड करा.',
      bank_passbook: '🏦 **बँक पासबुक** च्या पहिल्या पानाचा फोटो अपलोड करा.',
      aadhaar_card:  '🆔 **आधार कार्ड** (पुढची बाजू) चा स्पष्ट फोटो अपलोड करा.',
      voter_id:      '🗳️ **मतदार ओळखपत्र** (पुढची बाजू) चा स्पष्ट फोटो अपलोड करा.',
    },
    uploading:       '⏳ दस्तऐवज अपलोड होत आहे…',
    quality_check:   '🔍 गुणवत्ता तपासत आहे…',
    ocr_running:     '📖 AI ने वाचत आहे…',
    extracting:      '🔎 माहिती काढत आहे…',
    matching:        '🔗 जुळवत आहे…',
    fraud_check:     '🛡️ तपासत आहे…',
    done:            '✅ सत्यापन पूर्ण!',
    upload_another:  'आणखी दस्तऐवज अपलोड करायचा आहे का?',
    yes:             'हो, आणखी अपलोड करा',
    no:              'नाही, बस',
    goodbye:         '👋 धन्यवाद. सत्र संपले.',
    upload_error:    '❌ काहीतरी चूक झाली. पुन्हा प्रयत्न करा.',
    file_too_large:  '⚠️ फाइल खूप मोठी आहे.',
    invalid_type:    '⚠️ फक्त JPG, PNG किंवा WEBP.',
    inactivity:      'सत्र थांबवले.',
    inactivity_warn: '⚠️ 1 मिनिटात सत्र थांबेल.',
    resume:          'सत्र सुरू ठेवा',
    session_expired: 'सत्र संपले. **Restart** करा.',
    status_ask_id:   '🔍 **संदर्भ ID** टाका.',
    status_checking: '⏳ शोधत आहे…',
    status_not_found:'❌ दस्तऐवज सापडला नाही.',
    status_error:    '❌ स्थिती तपासता आली नाही.',
    check_status:    '🔍 स्थिती तपासा',
    retry_prompt:    'तुम्हाला काय करायचे आहे?',
    try_again:       '🔄 पुन्हा प्रयत्न करा',
    change_doc:      '🔀 वेगळा दस्तऐवज',
    cancel:          '✖ रद्द करा',
    type_hint_lang:  '**english**, **hindi**, किंवा **marathi** टाइप करा.',
    type_hint_doc:   'दस्तऐवजाचे नाव टाइप करा.',
    type_hint_upload:'📎 अटॅच बटण वापरा.',
    type_hint_ref:   'हा संदर्भ ID सारखा दिसत नाही.',
    switched_doc:    '**{doc}** निवडले.',
    doc_types: {
      land_record:   '🏞️ जमीन रेकॉर्ड',
      bank_passbook: '🏦 बँक पासबुक',
      aadhaar_card:  '🆔 आधार कार्ड',
      voter_id:      '🗳️ मतदार ओळखपत्र',
    },
  },
};

// ── Audio scripts ─────────────────────────────────────────────────────────────
const AUDIO_SCRIPTS = {
  en: {
    welcome:         'Welcome to FarmerVerify AI. Please select your language.',
    doc_prompt:      'Please choose the type of document you want to verify.',
    land_record:     'Please take a clear photo of your land record and upload it.',
    bank_passbook:   'Please take a clear photo of your bank passbook first page and upload it.',
    aadhaar_card:    'Please take a clear photo of your Aadhaar card front side and upload it.',
    voter_id:        'Please take a clear photo of your voter ID front side and upload it.',
    uploading:       'Your document is being uploaded. Please wait.',
    done_verified:   'Your document has been verified successfully.',
    done_review:     'Your document needs manual review. Our team will check it shortly.',
    done_rejected:   'Verification failed. Please try again with a clearer photo.',
    upload_another:  'Would you like to upload another document?',
    goodbye:         'Thank you for using FarmerVerify AI. Goodbye.',
    status_found:    'Here is the status of your document.',
    status_not_found:'No document was found with that reference ID.',
  },
  hi: {
    welcome:         'FarmerVerify AI में स्वागत है। भाषा चुनें।',
    doc_prompt:      'दस्तावेज़ का प्रकार चुनें।',
    land_record:     'जमीन रिकॉर्ड की स्पष्ट फोटो अपलोड करें।',
    bank_passbook:   'बैंक पासबुक के पहले पेज की स्पष्ट फोटो अपलोड करें।',
    aadhaar_card:    'आधार कार्ड की सामने की स्पष्ट फोटो अपलोड करें।',
    voter_id:        'मतदाता पहचान पत्र की सामने की स्पष्ट फोटो अपलोड करें।',
    uploading:       'दस्तावेज़ अपलोड हो रहा है।',
    done_verified:   'दस्तावेज़ सत्यापित हो गया।',
    done_review:     'दस्तावेज़ को समीक्षा की आवश्यकता है।',
    done_rejected:   'सत्यापन विफल। स्पष्ट फोटो के साथ पुनः प्रयास करें।',
    upload_another:  'क्या और दस्तावेज़ अपलोड करना है?',
    goodbye:         'धन्यवाद।',
    status_found:    'दस्तावेज़ की स्थिति।',
    status_not_found:'दस्तावेज़ नहीं मिला।',
  },
  mr: {
    welcome:         'FarmerVerify AI मध्ये स्वागत. भाषा निवडा.',
    doc_prompt:      'दस्तऐवजाचा प्रकार निवडा.',
    land_record:     'जमीन उताऱ्याचा स्पष्ट फोटो अपलोड करा.',
    bank_passbook:   'बँक पासबुकच्या पहिल्या पानाचा फोटो अपलोड करा.',
    aadhaar_card:    'आधार कार्डच्या पुढच्या बाजूचा फोटो अपलोड करा.',
    voter_id:        'मतदार ओळखपत्राच्या पुढच्या बाजूचा फोटो अपलोड करा.',
    uploading:       'दस्तऐवज अपलोड होत आहे.',
    done_verified:   'दस्तऐवज सत्यापित झाला.',
    done_review:     'दस्तऐवजाला तपासणी आवश्यक आहे.',
    done_rejected:   'सत्यापन अयशस्वी. पुन्हा प्रयत्न करा.',
    upload_another:  'आणखी दस्तऐवज अपलोड करायचा आहे का?',
    goodbye:         'धन्यवाद.',
    status_found:    'दस्तऐवजाची स्थिती.',
    status_not_found:'दस्तऐवज सापडला नाही.',
  },
};

// ── Input aliases ─────────────────────────────────────────────────────────────
const LANG_ALIASES = {
  'english': 'en', 'en': 'en', 'eng': 'en', '1': 'en',
  'hindi': 'hi', 'hi': 'hi', 'hin': 'hi', 'हिंदी': 'hi', '2': 'hi',
  'marathi': 'mr', 'mr': 'mr', 'mar': 'mr', 'मराठी': 'mr', '3': 'mr',
};

const DOC_ALIASES = {
  'land': 'land_record', 'land record': 'land_record', 'land_record': 'land_record',
  '7/12': 'land_record', 'satbara': 'land_record',
  'जमीन': 'land_record', 'जमीन रिकॉर्ड': 'land_record', 'जमीन रेकॉर्ड': 'land_record',
  '1': 'land_record',
  'bank': 'bank_passbook', 'passbook': 'bank_passbook', 'bank passbook': 'bank_passbook',
  'bank_passbook': 'bank_passbook', 'पासबुक': 'bank_passbook',
  '2': 'bank_passbook',
  'aadhaar': 'aadhaar_card', 'aadhar': 'aadhaar_card', 'aadhaar card': 'aadhaar_card',
  'aadhaar_card': 'aadhaar_card', 'आधार': 'aadhaar_card', 'आधार कार्ड': 'aadhaar_card',
  '3': 'aadhaar_card',
  'voter': 'voter_id', 'voter id': 'voter_id', 'voter_id': 'voter_id',
  'epic': 'voter_id', 'मतदार': 'voter_id', 'मतदाता': 'voter_id',
  '4': 'voter_id',
};

const STATUS_TRIGGERS = [
  'check status', 'status', 'check', 'reference', 'ref id', 'ref',
  'स्थिति', 'स्थिति जाँचें', 'स्थिती', 'स्थिती तपासा',
];

function looksLikeRefId(text) {
  return /^[a-f0-9]{8,12}$/i.test(text.trim());
}

// ── State ─────────────────────────────────────────────────────────────────────
let state = {
  lang: null,
  docType: null,
  step: 'lang_select',
  processing: false,
  muted: false,
  inactive: false,
  sessionEnded: false,
};

let inactivityTimer = null;
let warnTimer = null;
let expireTimer = null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const chatWindow       = document.getElementById('chatWindow');
const textInput        = document.getElementById('textInput');
const sendBtn          = document.getElementById('sendBtn');
const attachBtn        = document.getElementById('attachBtn');
const fileInput        = document.getElementById('fileInput');
const progressBar      = document.getElementById('progressBar');
const progressLabel    = document.getElementById('progressLabel');
const imageModal       = document.getElementById('imageModal');
const modalImage       = document.getElementById('modalImage');
const modalClose       = document.getElementById('modalClose');
const muteBtn          = document.getElementById('muteBtn');
const resetBtn         = document.getElementById('resetBtn');
const inactivityBanner = document.getElementById('inactivityBanner');
const inactivityMsg    = document.getElementById('inactivityMsg');
const resumeBtn        = document.getElementById('resumeBtn');
const statusDot        = document.getElementById('statusDot');
const statusText       = document.getElementById('statusText');

// ── Helpers ───────────────────────────────────────────────────────────────────
const t     = (key) => STRINGS[state.lang || 'en']?.[key] ?? STRINGS.en[key] ?? key;
const audio = (key) => AUDIO_SCRIPTS[state.lang || 'en']?.[key] ?? AUDIO_SCRIPTS.en[key] ?? '';

function scrollBottom() { chatWindow.scrollTop = chatWindow.scrollHeight; }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function renderMd(text) {
  if (typeof text !== 'string') return '';
  return text
    .replace(/`([^`]+)`/g, '<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:11px">$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/_\((.+?)\)_/g, '<em style="font-size:11px;color:#888">($1)</em>')
    .replace(/\n/g, '<br/>');
}

// ── Safe message extractor — never throws ─────────────────────────────────────
function getResultMessage(result) {
  try {
    if (!result) return '';
    const lang = state.lang || 'en';
    if (result.messages && typeof result.messages === 'object') {
      return result.messages[lang] || result.messages.en || '';
    }
    return result.message || '';
  } catch (e) {
    return '';
  }
}

// ── Audio ─────────────────────────────────────────────────────────────────────
function speak(text, lang = state.lang || 'en') {
  if (state.muted || !text) return;
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  const langMap = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };
  utter.lang = langMap[lang] || 'en-IN';
  utter.rate = 0.88;
  utter.pitch = 1.0;
  window.speechSynthesis.speak(utter);
}

// ── Message renderers ─────────────────────────────────────────────────────────
function addMessage(role, content) {
  if (state.sessionEnded && role !== 'system') return;
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  avatar.textContent = role === 'bot' ? '🌳' : '👤';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if (typeof content === 'string') {
    bubble.innerHTML = renderMd(content);
  } else if (content instanceof HTMLElement) {
    bubble.appendChild(content);
  } else {
    bubble.textContent = String(content || '');
  }
  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatWindow.appendChild(wrapper);
  scrollBottom();
  return bubble;
}

function addAudioBubble(audioKey) {
  const text = audio(audioKey);
  if (!text) return;
  const wrapper = document.createElement('div');
  wrapper.className = 'message bot';
  const av = document.createElement('div');
  av.className = 'msg-avatar';
  av.textContent = '🌳';
  const outer = document.createElement('div');
  outer.className = 'msg-bubble';
  outer.style.padding = '6px 0';
  outer.style.background = 'transparent';
  const bub = document.createElement('div');
  bub.className = 'audio-bubble';
  bub.title = 'Tap to hear audio';
  const playBtn = document.createElement('button');
  playBtn.className = 'audio-play-btn';
  playBtn.textContent = '▶';
  const wave = document.createElement('div');
  wave.className = 'audio-wave';
  const dur = document.createElement('span');
  dur.className = 'audio-duration';
  dur.textContent = '🔊 Audio';
  bub.appendChild(playBtn);
  bub.appendChild(wave);
  bub.appendChild(dur);
  outer.appendChild(bub);

  const handlePlay = () => {
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      playBtn.textContent = '▶';
      playBtn.classList.remove('playing');
    } else {
      playBtn.textContent = '⏸';
      playBtn.classList.add('playing');
      const utter = new SpeechSynthesisUtterance(text);
      const langMap = { en: 'en-IN', hi: 'hi-IN', mr: 'mr-IN' };
      utter.lang = langMap[state.lang || 'en'] || 'en-IN';
      utter.rate = 0.88;
      utter.onend = () => { playBtn.textContent = '▶'; playBtn.classList.remove('playing'); };
      window.speechSynthesis.speak(utter);
    }
  };

  bub.addEventListener('click', handlePlay);
  wrapper.appendChild(av);
  wrapper.appendChild(outer);
  chatWindow.appendChild(wrapper);
  scrollBottom();
  if (!state.muted) handlePlay();
}

function addTyping() {
  const w = document.createElement('div');
  w.className = 'message bot';
  w.id = 'typing-ind';
  const av = document.createElement('div');
  av.className = 'msg-avatar';
  av.textContent = '🌳';
  const bub = document.createElement('div');
  bub.className = 'msg-bubble';
  bub.innerHTML = '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';
  w.appendChild(av);
  w.appendChild(bub);
  chatWindow.appendChild(w);
  scrollBottom();
}

function removeTyping() {
  const el = document.getElementById('typing-ind');
  if (el) el.remove();
}

// ── Quick replies ─────────────────────────────────────────────────────────────
function addQuickReplies(options, onSelect) {
  const wrapper = document.createElement('div');
  wrapper.className = 'message bot';
  wrapper.id = 'qr-wrapper';
  const av = document.createElement('div');
  av.className = 'msg-avatar';
  av.textContent = '🌳';
  const outer = document.createElement('div');
  outer.className = 'msg-bubble';
  outer.style.background = 'transparent';
  outer.style.padding = '0';
  const qr = document.createElement('div');
  qr.className = 'quick-replies';
  options.forEach(({ label, value }) => {
    const btn = document.createElement('button');
    btn.className = 'qr-btn';
    btn.textContent = label;
    btn.addEventListener('click', () => {
      qr.querySelectorAll('.qr-btn').forEach(b => { b.disabled = true; b.classList.remove('selected'); });
      btn.classList.add('selected');
      onSelect(value, label);
    });
    qr.appendChild(btn);
  });
  outer.appendChild(qr);
  wrapper.appendChild(av);
  wrapper.appendChild(outer);
  chatWindow.appendChild(wrapper);
  scrollBottom();
}

function removeQuickReplies() {
  const el = document.getElementById('qr-wrapper');
  if (el) el.remove();
}

// ── Progress ──────────────────────────────────────────────────────────────────
function showProgress(label) {
  progressLabel.textContent = label;
  progressBar.style.display = 'flex';
}
function hideProgress() { progressBar.style.display = 'none'; }

// ── Image modal ───────────────────────────────────────────────────────────────
function openModal(src) { modalImage.src = src; imageModal.style.display = 'flex'; }
modalClose.addEventListener('click', () => { imageModal.style.display = 'none'; });
imageModal.addEventListener('click', e => { if (e.target === imageModal) imageModal.style.display = 'none'; });

// ── Inactivity ────────────────────────────────────────────────────────────────
function resetInactivityTimer() {
  if (state.sessionEnded) return;
  clearTimeout(inactivityTimer);
  clearTimeout(warnTimer);
  clearTimeout(expireTimer);
  hideBanner();
  warnTimer = setTimeout(() => {
    if (!state.sessionEnded) { addMessage('bot', t('inactivity_warn')); speak(t('inactivity_warn')); }
  }, CONFIG.INACTIVITY_TIMEOUT_MS - 60000);
  inactivityTimer = setTimeout(() => {
    if (!state.sessionEnded) pauseSession();
  }, CONFIG.INACTIVITY_TIMEOUT_MS);
}

function pauseSession() {
  state.inactive = true;
  inactivityMsg.textContent = t('inactivity');
  inactivityBanner.style.display = 'flex';
  statusDot.className = 'status-dot busy';
  statusText.textContent = 'Paused';
  expireTimer = setTimeout(expireSession, CONFIG.RESUME_TIMEOUT_MS);
}

function hideBanner() { inactivityBanner.style.display = 'none'; state.inactive = false; }

function expireSession() {
  state.sessionEnded = true;
  hideBanner();
  statusDot.className = 'status-dot offline';
  statusText.textContent = 'Session Ended';
  addMessage('bot', t('session_expired'));
  textInput.disabled = true;
  sendBtn.disabled = true;
  attachBtn.style.display = 'none';
}

resumeBtn.addEventListener('click', () => {
  clearTimeout(expireTimer);
  hideBanner();
  state.inactive = false;
  statusDot.className = 'status-dot online';
  statusText.textContent = 'Online';
  resetInactivityTimer();
  let resumeMsg = '👋 Welcome back! ';
  if (state.step === 'upload') resumeMsg += t('upload_prompt')[state.docType] || '';
  else if (state.step === 'doc_select') resumeMsg += t('doc_prompt');
  else if (state.step === 'status_check') resumeMsg += t('status_ask_id');
  addMessage('bot', resumeMsg);
});

['click', 'keydown', 'touchstart'].forEach(evt => {
  document.addEventListener(evt, () => {
    if (!state.sessionEnded && !state.inactive) resetInactivityTimer();
  });
});

// ── Text input handler ────────────────────────────────────────────────────────
async function handleTextInput(rawText) {
  const text = rawText.trim();
  if (!text || state.processing || state.sessionEnded) return;
  const lower = text.toLowerCase().trim();
  resetInactivityTimer();

  if (looksLikeRefId(text)) { addMessage('user', text); await checkDocumentStatus(text.trim()); return; }
  if (STATUS_TRIGGERS.some(tr => lower.includes(tr))) { addMessage('user', text); await startStatusCheck(); return; }

  switch (state.step) {
    case 'lang_select': {
      const lang = LANG_ALIASES[lower];
      if (lang) {
        state.lang = lang;
        removeQuickReplies();
        addMessage('user', { en: '🇬🇧 English', hi: '🇮🇳 हिंदी', mr: '🇮🇳 मराठी' }[lang] || text);
        await sleep(400); startDocSelect();
      } else { addMessage('user', text); addMessage('bot', '❓ ' + t('type_hint_lang')); }
      break;
    }
    case 'doc_select': {
      const docType = DOC_ALIASES[lower];
      if (docType) {
        state.docType = docType; removeQuickReplies();
        addMessage('user', t('doc_types')[docType] || docType);
        await sleep(400); startUploadStep();
      } else { addMessage('user', text); addMessage('bot', '❓ ' + t('type_hint_doc')); }
      break;
    }
    case 'upload': {
      addMessage('user', text);
      const docType = DOC_ALIASES[lower];
      if (docType) {
        state.docType = docType;
        addMessage('bot', t('switched_doc').replace('{doc}', t('doc_types')[docType] || docType));
        attachBtn.style.display = 'flex';
      } else { addMessage('bot', '❓ ' + t('type_hint_upload')); }
      break;
    }
    case 'status_check': {
      addMessage('user', text);
      if (looksLikeRefId(text)) await checkDocumentStatus(text.trim());
      else addMessage('bot', '❓ ' + t('type_hint_ref'));
      break;
    }
    default: { addMessage('user', text); addMessage('bot', '❓ ' + t('type_hint_doc')); break; }
  }
}

// ── Status checker ────────────────────────────────────────────────────────────
async function startStatusCheck() {
  state.step = 'status_check';
  attachBtn.style.display = 'none';
  addTyping();
  await sleep(CONFIG.BOT_DELAY_MS);
  removeTyping();
  addMessage('bot', t('status_ask_id'));
  textInput.placeholder = 'Enter Reference ID…';
  textInput.focus();
}

async function checkDocumentStatus(requestId) {
  addTyping();
  showProgress(t('status_checking'));
  try {
    const resp = await fetch(`${CONFIG.API_BASE}/api/v1/status/${requestId}`);
    hideProgress();
    removeTyping();
    if (resp.status === 404) { addMessage('bot', t('status_not_found')); await sleep(400); addStatusRetryOptions(); return; }
    if (!resp.ok) { addMessage('bot', t('status_error')); await sleep(400); addStatusRetryOptions(); return; }
    const result = await resp.json();
    addAudioBubble('status_found');
    try { addMessage('bot', buildFarmerCard(result)); } catch (e) { console.warn('card error', e); }
    const msg = getResultMessage(result);
    if (msg) addMessage('bot', msg);
    await sleep(800);
    addStatusRetryOptions();
  } catch (err) {
    hideProgress(); removeTyping();
    console.error('Status check error:', err);
    addMessage('bot', t('status_error'));
    await sleep(400); addStatusRetryOptions();
  }
}

async function addStatusRetryOptions() {
  await sleep(400);
  const lang = state.lang || 'en';
  const checkL  = { en: 'Check Another', hi: 'और जाँचें', mr: 'आणखी तपासा' };
  const uploadL = { en: 'Upload Document', hi: 'दस्तावेज़ अपलोड करें', mr: 'दस्तऐवज अपलोड करा' };
  addQuickReplies([
    { label: '🔍 ' + (checkL[lang]  || checkL.en),  value: 'check_again' },
    { label: '📄 ' + (uploadL[lang] || uploadL.en), value: 'upload' },
    { label: t('no') || 'Done', value: 'done' },
  ], async (val, label) => {
    addMessage('user', label);
    resetInactivityTimer();
    await sleep(300);
    if (val === 'check_again') { await startStatusCheck(); }
    else if (val === 'upload') { state.step = 'doc_select'; state.docType = null; await startDocSelect(); }
    else { endSession(); }
  });
}

// ── Chat flow ─────────────────────────────────────────────────────────────────
function startLangSelect() {
  state.step = 'lang_select';
  textInput.placeholder = 'Type: english, hindi, or marathi…';
  setTimeout(async () => {
    addTyping(); await sleep(CONFIG.BOT_DELAY_MS); removeTyping();
    addMessage('bot', STRINGS.en.lang_prompt);
    speak(AUDIO_SCRIPTS.en.welcome, 'en');
    addQuickReplies([
      { label: '🇬🇧 English', value: 'en' },
      { label: '🇮🇳 हिंदी',    value: 'hi' },
      { label: '🇮🇳 मराठी',    value: 'mr' },
    ], async (lang, label) => {
      state.lang = lang;
      addMessage('user', label);
      resetInactivityTimer();
      await sleep(400); startDocSelect();
    });
  }, 300);
}

async function startDocSelect() {
  state.step = 'doc_select';
  textInput.placeholder = 'Type document name or "check status"…';
  attachBtn.style.display = 'none';
  addTyping(); await sleep(CONFIG.BOT_DELAY_MS); removeTyping();
  addMessage('bot', t('doc_prompt'));
  addAudioBubble('doc_prompt');
  const docTypes = t('doc_types');
  const options  = Object.entries(docTypes).map(([value, label]) => ({ label, value }));
  options.push({ label: t('check_status'), value: 'check_status' });
  addQuickReplies(options, async (val, label) => {
    if (val === 'check_status') { addMessage('user', label); resetInactivityTimer(); await startStatusCheck(); return; }
    state.docType = val;
    addMessage('user', label);
    resetInactivityTimer();
    await sleep(400); startUploadStep();
  });
}

async function startUploadStep() {
  state.step = 'upload';
  textInput.placeholder = 'Tap 📎 to attach, or type "check status"…';
  addTyping(); await sleep(CONFIG.BOT_DELAY_MS); removeTyping();
  addMessage('bot', t('upload_prompt')[state.docType] || '');

  // ── PDF hint for land record and meeting minutes ───────────────────────
  if (state.docType === 'land_record' || state.docType === 'meeting_minutes') {
    const pdfHint = {
      en: '💡 **Tip:** You can also upload a **multi-page PDF** containing Land Record, CC Training Photo, and Minutes of Meeting — all in one go!',
      hi: '💡 **सुझाव:** आप एक **बहु-पृष्ठ PDF** भी अपलोड कर सकते हैं जिसमें सभी दस्तावेज़ हों!',
      mr: '💡 **टीप:** तुम्ही एक **बहु-पान PDF** अपलोड करू शकता ज्यात सर्व दस्तऐवज असतील!',
    };
    const lang = state.lang || 'en';
    addMessage('bot', pdfHint[lang] || pdfHint.en);
  }

  addAudioBubble(state.docType);
  attachBtn.style.display = 'flex';
}

// ── Process document — THE FIXED FUNCTION ────────────────────────────────────
async function processDocument(file) {
  if (state.processing) return;
  state.processing = true;
  sendBtn.disabled = true;
  attachBtn.style.display = 'none';
  resetInactivityTimer();

  const objectUrl = URL.createObjectURL(file);

  // Show preview bubble
  const wrapper = document.createElement('div');
  wrapper.className = 'message user';
  const av  = document.createElement('div'); av.className = 'msg-avatar'; av.textContent = '👤';
  const bub = document.createElement('div'); bub.className = 'msg-bubble'; bub.style.padding = '6px'; bub.style.background = 'transparent';
  const previewCard = document.createElement('div'); previewCard.className = 'doc-preview-card';
  previewCard.innerHTML = `<img src="${objectUrl}" /><div class="doc-preview-label">📄 ${file.name}</div>`;
  previewCard.addEventListener('click', () => openModal(objectUrl));
  bub.appendChild(previewCard); wrapper.appendChild(av); wrapper.appendChild(bub);
  chatWindow.appendChild(wrapper); scrollBottom();

  // Local file validation
  const isPdf = file.type === 'application/pdf' ||
                file.name.toLowerCase().endsWith('.pdf');

  if (!isPdf && !CONFIG.ALLOWED_TYPES.includes(file.type)) {
    addMessage('bot', t('invalid_type')); speak(t('invalid_type'));
    resetProc(); return;
  }
  if (file.size > CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024) {
    addMessage('bot', t('file_too_large')); speak(t('file_too_large'));
    resetProc(); return;
  }

  // ── PDF early message ─────────────────────────────────────────────────────
  if (isPdf) {
    addMessage('bot', t('pdf_detected'));
    speak(t('pdf_detected'));
  }

  const pipelineSteps = [
    { key: 'uploading',     delay: 600  },
    { key: 'quality_check', delay: 800  },
    { key: 'ocr_running',   delay: 1200 },
    { key: 'extracting',    delay: 600  },
    { key: 'matching',      delay: 600  },
    { key: 'fraud_check',   delay: 600  },
  ];

  // ── Make the API call ────────────────────────────────────────
  let result = null;

  showProgress(t('uploading'));
  addTyping();
  speak(audio('uploading'));

  try {
    const apiPromise = uploadDocument(file, state.docType, isPdf);

    for (const step of pipelineSteps) {
      showProgress(t(step.key));
      await sleep(step.delay);
    }

    result = await apiPromise;

  } catch (networkErr) {
    // Only network / HTTP errors reach here (e.g., server down, 500, timeout)
    hideProgress();
    removeTyping();
    
    console.error('NETWORK ERROR during upload:', networkErr);
    addMessage('bot', t('upload_error'));
    speak(audio('done_rejected'));
    await sleep(800);
    resetProc();
    await askUploadAnother();
    console.log('=== FULL API RESULT ===', JSON.stringify(result, null, 2));
    return;
  }

  // ── API succeeded — handle result ────────────────────────────
  // This block is completely separate from the network try/catch above.
  // Any error here will be caught by ITS OWN try/catch and never
  // show "something went wrong".
  hideProgress();
  removeTyping();

  // Log for debugging — check browser console to see exact payload
  console.log('=== UPLOAD RESULT ===', result);

  try {
    // ── PDF BATCH RESULT HANDLING ─────────────────────────────────────────
    if (result && result.is_batch === true) {
      await handlePdfBatchResult(result);
      resetProc();
      await askUploadAnother();
      return;
    }

    // Safe status extraction — single document flow continues below
    const status = (result && typeof result.status === 'string') ? result.status : 'needs_review';

    // Safe message extraction
    let msg = '';
    try {
      if (result && result.messages && result.messages[lang]) {
        msg = result.messages[lang];
      } else if (result && result.messages && result.messages.en) {
        msg = result.messages.en;
      } else if (result && typeof result.message === 'string') {
        msg = result.message;
      }
    } catch (_) { msg = ''; }

    // ── REJECTED ────────────────────────────────────────────────
    if (status === 'rejected') {
      addMessage('bot', msg || '❌ Document could not be verified. Please try again.');
      addAudioBubble('done_rejected');
      await sleep(800);
      resetProc();
      await addRetryOption();
      return;
    }

    // ── DUPLICATE ───────────────────────────────────────────────
    if (status === 'duplicate') {
      addMessage('bot', msg || 'ℹ️ This document was already submitted.');
      addAudioBubble('done_review');
      await sleep(600);
      try {
        addMessage('bot', buildFarmerCard(result));
      } catch (cardErr) {
        console.warn('Card build error (duplicate):', cardErr);
        const origId = (result && result.original_request_id) || (result && result.request_id) || 'N/A';
        addMessage('bot', `ℹ️ Already submitted.\nOriginal Reference ID: **${origId}**`);
      }
      await sleep(800);
      resetProc();
      await askUploadAnother();
      return;
    }

    // ── VERIFIED / NEEDS_REVIEW (success path) ───────────────────
    addMessage('bot', t('done'));
    addAudioBubble(status === 'verified' ? 'done_verified' : 'done_review');

    // Build result card — with total fallback if card builder fails
    const isVerified   = result.status === 'verified';
const isNeedsReview = result.status === 'needs_review';

if (isVerified) {
  addMessage('bot', t('done'));         // "✅ Verification complete!"
  addAudioBubble('done_verified');
} else {
  // needs_review or any other passing status
  addMessage('bot', '📤 Document uploaded successfully!');
  addAudioBubble('done_review');
}

// Build result card
try {
  addMessage('bot', buildFarmerCard(result));
} catch (cardErr) {
  console.warn('buildFarmerCard error:', cardErr);
  addMessage('bot', `📋 Uploaded.\nReference ID: **${result.request_id || 'N/A'}**`);
}

// Show the status message from server
const statusMsg = getResultMessage(result);
if (statusMsg) addMessage('bot', statusMsg);

await sleep(1200);
resetProc();
await askUploadAnother();

  } catch (handleErr) {
    // Absolute safety net — should NEVER be reached with the above guards
    console.error('RESULT HANDLER CRASH:', handleErr);
    console.error('Result object was:', result);
    // Show useful info even if everything crashed
    const rid = (result && result.request_id) ? result.request_id : 'N/A';
    const st  = (result && result.status)     ? result.status     : 'processed';
    addMessage('bot',
      `✅ Your document has been uploaded and is being reviewed.\n\n` +
      `**Reference ID:** ${rid}\n` +
      `**Status:** ${st}\n\n` +
      `_Use this Reference ID to check your status later._`
    );
    resetProc();
    await askUploadAnother();
  }

  function resetProc() {
    state.processing = false;
    sendBtn.disabled = false;
    attachBtn.style.display = 'flex';
    URL.revokeObjectURL(objectUrl);
  }
}

// ── PDF Batch Result Handler — CLEAN FINAL VERSION ───────────────────────────
async function handlePdfBatchResult(batchResult) {
  const lang       = state.lang || 'en';
  const mainRefId  = batchResult.batch_id || batchResult.request_id || 'N/A';
  const mainStatus = batchResult.status   || 'needs_review';
  const totalPages = batchResult.total_pages || 0;
  const summary    = batchResult.summary  || {};
  const verified   = summary.verified     || 0;
  const review     = summary.needs_review || 0;
  const rejected   = summary.rejected     || 0;
  const results    = batchResult.results  || [];

  // ── Step 1: One clean summary line ───────────────────────────────────────
  const summaryMsg = {
    en: `✅ Your documents have been received and are being processed by our team.`,
    hi: `✅ आपके दस्तावेज़ प्राप्त हो गए हैं और हमारी टीम उन्हें जाँच रही है।`,
    mr: `✅ तुमचे दस्तऐवज मिळाले आहेत आणि आमची टीम त्यांची तपासणी करत आहे.`,
  };
  addMessage('bot', summaryMsg[lang] || summaryMsg.en);
  addAudioBubble(mainStatus === 'verified' ? 'done_verified' : 'done_review');

  await sleep(500);

  // ── Step 2: ONE result card — single reference ID ─────────────────────────
  const unifiedResult = {
    request_id:       mainRefId,
    status:           mainStatus,
    document_type:    batchResult.document_type
                      || (results[0] && results[0].document_type)
                      || 'land_record',
    extracted_fields: batchResult.extracted_fields || {},
    messages:         batchResult.messages || {},
    message:          batchResult.message  || '',
  };

  try {
    addMessage('bot', buildFarmerCard(unifiedResult));
  } catch (cardErr) {
    console.warn('PDF card error:', cardErr);
    addMessage('bot', `📋 PDF uploaded.\n**Reference ID:** \`${mainRefId}\``);
  }

  await sleep(400);

  // ── Step 3: One friendly server message ───────────────────────────────────
  const serverMsg = (batchResult.messages?.[lang])
                    || (batchResult.messages?.en)
                    || batchResult.message
                    || '';
  if (serverMsg) addMessage('bot', serverMsg);

  // ── Step 4: Only show a tip IF pages were rejected — no page breakdown ────
  const rejectedPages   = results.filter(r => r.status === 'rejected');
  const qualityRejected = rejectedPages.filter(r => r.rejection_type === 'quality');
  const ccRejected      = rejectedPages.filter(r => r.rejection_type === 'insufficient_persons');

  if (qualityRejected.length > 0) {
    await sleep(400);
    const tip = {
      en: `📷 **Note:** ${qualityRejected.length} of your document page(s) could not be read clearly due to poor image quality. Our team will contact you if a retake is needed.`,
      hi: `📷 **नोट:** ${qualityRejected.length} पेज धुंधले थे। यदि दोबारा फोटो की ज़रूरत होगी, टीम आपसे संपर्क करेगी।`,
      mr: `📷 **टीप:** ${qualityRejected.length} पाने अस्पष्ट होती. पुन्हा फोटो आवश्यक असल्यास टीम संपर्क करेल.`,
    };
    addMessage('bot', tip[lang] || tip.en);
  }

  if (ccRejected.length > 0) {
    await sleep(400);
    const tip = {
      en: `📸 **Note:** Your CC Training photo must show both the farmer and the field representative together. Our team will let you know if a new photo is required.`,
      hi: `📸 **नोट:** CC फोटो में किसान और प्रतिनिधि दोनों दिखने चाहिए।`,
      mr: `📸 **टीप:** CC फोटोमध्ये शेतकरी आणि प्रतिनिधी दोघेही दिसले पाहिजेत.`,
    };
    addMessage('bot', tip[lang] || tip.en);
  }

  // ── Step 5: ONE reference ID — clearly stated ─────────────────────────────
  await sleep(400);
  const refMsg = {
    en: `📋 **Your Reference ID:** \`${mainRefId}\`\nSave this to check your document status later.`,
    hi: `📋 **आपकी संदर्भ ID:** \`${mainRefId}\`\nबाद में स्थिति जाँचने के लिए सहेजें।`,
    mr: `📋 **तुमचा संदर्भ ID:** \`${mainRefId}\`\nनंतर स्थिती तपासण्यासाठी हा ID जतन करा.`,
  };
  addMessage('bot', refMsg[lang] || refMsg.en);

  await sleep(400);
}
// ── Retry after rejection ─────────────────────────────────────────────────────
async function addRetryOption() {
  state.processing = false;
  sendBtn.disabled = false;
  addTyping(); await sleep(CONFIG.BOT_DELAY_MS); removeTyping();
  addMessage('bot', t('retry_prompt'));
  addQuickReplies([
    { label: t('try_again'),  value: 'retry_same' },
    { label: t('change_doc'), value: 'change_type' },
    { label: t('cancel'),     value: 'cancel' },
  ], async (val, label) => {
    addMessage('user', label);
    resetInactivityTimer();
    await sleep(300);
    if (val === 'retry_same') {
      state.step = 'upload';
      attachBtn.style.display = 'flex';
      textInput.placeholder = 'Tap 📎 to attach…';
      addTyping(); await sleep(500); removeTyping();
      addMessage('bot', t('upload_prompt')[state.docType] || '');
      addAudioBubble(state.docType);
    } else if (val === 'change_type') {
      state.docType = null; state.step = 'doc_select';
      attachBtn.style.display = 'none';
      await sleep(300); startDocSelect();
    } else {
      await sleep(300); await askUploadAnother();
    }
  });
}

// ── Ask upload another ────────────────────────────────────────────────────────
async function askUploadAnother() {
  state.processing = false;
  sendBtn.disabled = false;
  addTyping(); await sleep(CONFIG.BOT_DELAY_MS); removeTyping();
  addMessage('bot', t('upload_another'));
  speak(audio('upload_another'));
  const lang    = state.lang || 'en';
  const checkL  = { en: 'Check Status', hi: 'स्थिति जाँचें', mr: 'स्थिती तपासा' };
  addQuickReplies([
    { label: t('yes'),                          value: 'yes' },
    { label: '🔍 ' + (checkL[lang] || checkL.en), value: 'check_status' },
    { label: t('no'),                           value: 'no' },
  ], async (val, label) => {
    addMessage('user', label);
    resetInactivityTimer();
    await sleep(300);
    if (val === 'yes') { state.docType = null; state.step = 'doc_select'; await sleep(400); startDocSelect(); }
    else if (val === 'check_status') { await startStatusCheck(); }
    else { endSession(); }
  });
}

function endSession() {
  addMessage('bot', t('goodbye'));
  speak(audio('goodbye'));
  state.step = 'done';
  state.sessionEnded = true;
  textInput.disabled = true;
  sendBtn.disabled = true;
  attachBtn.style.display = 'none';
  statusDot.className = 'status-dot offline';
  statusText.textContent = 'Session Ended';
}

// ── API ───────────────────────────────────────────────────────────────────────
async function uploadDocument(file, docType, isPdf = false) {
  const fd = new FormData();
  fd.append('file', file);

  // ── For PDF — send as auto so backend handles each page independently ──
  fd.append('document_type', isPdf ? (docType || 'land_record') : docType);
  fd.append('language', state.lang || 'en');

  const resp = await fetch(`${CONFIG.API_BASE}/api/v1/upload/document`, {
    method: 'POST',
    body: fd,
  });

  if (!resp.ok) {
    const errText = await resp.text().catch(() => `HTTP ${resp.status}`);
    throw new Error(`Upload failed: ${resp.status} — ${errText}`);
  }

  // Parse JSON safely
  const text = await resp.text();

  if (!text || text.trim() === '' || text.trim() === 'null') {
    throw new Error(`Server returned empty response (status ${resp.status}). Check backend logs.`);
  }

  let data;
  try {
    data = JSON.parse(text);
  } catch (parseErr) {
    throw new Error(`Server returned invalid JSON: ${text.slice(0, 200)}`);
  }

  if (!data || typeof data !== 'object') {
    throw new Error(`Server returned null or non-object response: ${text.slice(0, 200)}`);
  }

  return data;
}
// ── Result card ───────────────────────────────────────────────────────────────
function buildFarmerCard(result) {
  // Safe defaults — never throw
  const status = (result && result.status) || 'needs_review';
  const lang   = state.lang || 'en';

  const statusConfig = {
  verified:     { icon: '✅', color: '#2d6a4f', bg: '#d8f3dc',
                  label: { en: 'Verified & Approved', hi: 'सत्यापित व स्वीकृत', mr: 'सत्यापित व मंजूर' } },
  needs_review: { icon: '📤', color: '#1565c0', bg: '#e3f2fd',
                  label: { en: 'Uploaded — Under Review', hi: 'अपलोड — समीक्षाधीन', mr: 'अपलोड — पुनरावलोकनाधीन' } },
  rejected:     { icon: '❌', color: '#c62828', bg: '#fde8e8',
                  label: { en: 'Not Accepted', hi: 'अस्वीकृत', mr: 'नाकारले' } },
  duplicate:    { icon: 'ℹ️', color: '#1565c0', bg: '#e3f2fd',
                  label: { en: 'Already Submitted', hi: 'पहले से जमा', mr: 'आधीच सादर' } },

                  processed:    {
      icon: '📤', color: '#1565c0', bg: '#e3f2fd',
      label: { en: 'Uploaded — Under Review', hi: 'अपलोड — समीक्षाधीन', mr: 'अपलोड — पुनरावलोकनाधीन' }
    },

    pending:      {
      icon: '⏳', color: '#e65100', bg: '#fff3e0',
      label: { en: 'Processing', hi: 'प्रक्रियाधीन', mr: 'प्रक्रिया सुरू' }
    },
    flagged:      {
      icon: '🚩', color: '#c62828', bg: '#fde8e8',
      label: { en: 'Flagged for Review', hi: 'समीक्षा के लिए फ्लैग', mr: 'पुनरावलोकनासाठी फ्लॅग' }

    },

  
};

  
  const cfg = statusConfig[status] || statusConfig.needs_review;
  const fields = (result && result.extracted_fields) ? result.extracted_fields : {};

  const fieldDefs = {
    aadhaar_card: [
      { key: 'name',          labels: { en: 'Name',          hi: 'नाम',      mr: 'नाव' } },
      { key: 'date_of_birth', labels: { en: 'Date of Birth', hi: 'जन्मतिथि', mr: 'जन्मतारीख' } },
      { key: 'gender',        labels: { en: 'Gender',        hi: 'लिंग',     mr: 'लिंग' } },
    ],
    bank_passbook: [
      { key: 'name',           labels: { en: 'Account Holder', hi: 'खाताधारक',  mr: 'खातेदार' } },
      { key: 'account_number', labels: { en: 'Account No.',    hi: 'खाता नंबर', mr: 'खाते क्र.' } },
      { key: 'bank_name',      labels: { en: 'Bank',           hi: 'बैंक',      mr: 'बँक' } },
    ],
    land_record: [
      { key: 'name',          labels: { en: 'Owner Name', hi: 'मालिक का नाम', mr: 'मालकाचे नाव' } },
      { key: 'village',       labels: { en: 'Village',    hi: 'गाँव',         mr: 'गाव' } },
      { key: 'district',      labels: { en: 'District',   hi: 'जिला',         mr: 'जिल्हा' } },
      { key: 'survey_number', labels: { en: 'Survey No.', hi: 'सर्वे नंबर',   mr: 'सर्वे क्र.' } },
    ],
    voter_id: [
      { key: 'name',     labels: { en: 'Voter Name', hi: 'मतदाता नाम', mr: 'मतदाराचे नाव' } },
      { key: 'district', labels: { en: 'District',   hi: 'जिला',       mr: 'जिल्हा' } },
    ],
  };

  const defs = fieldDefs[result && result.document_type] || [];
  let fieldsHtml = '';

  if (status !== 'rejected') {
    defs.forEach(({ key, labels }) => {
      const val = fields[key];
      if (val) {
        fieldsHtml += `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f0f0f0">
          <span style="color:#666;font-size:12px">${labels[lang] || labels.en}</span>
          <span style="font-weight:500;font-size:12px;text-align:right;max-width:60%">${val}</span>
        </div>`;
      }
    });
  }

  const docTypeDisplay = ((result && result.document_type) || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  const displayId = status === 'duplicate'
    ? ((result && result.original_request_id) || (result && result.request_id) || 'N/A')
    : ((result && result.request_id) || 'N/A');

  const refHints = {
    en: 'Save this ID to check status later',
    hi: 'स्थिति जाँचने के लिए यह ID सहेजें',
    mr: 'स्थिती तपासण्यासाठी हा ID जतन करा',
  };
  const dupHints = {
    en: 'Reference ID of your previously submitted document',
    hi: 'यह पहले से सबमिट किया गया दस्तावेज़ का ID है',
    mr: 'हे आधीच सादर केलेल्या दस्तऐवजाचे ID आहे',
  };

  const card = document.createElement('div');
  card.style.cssText = 'background:#fff;border:1px solid ' + cfg.color + '44;border-radius:12px;overflow:hidden;min-width:240px;margin-top:4px;';
  card.innerHTML = `
    <div style="background:${cfg.bg};padding:12px 14px;display:flex;align-items:center;gap:10px">
      <span style="font-size:24px">${cfg.icon}</span>
      <div>
        <div style="font-weight:700;font-size:14px;color:${cfg.color}">${cfg.label[lang] || cfg.label.en}</div>
        <div style="font-size:11px;color:#888">${docTypeDisplay}</div>
      </div>
    </div>
    ${fieldsHtml ? `<div style="padding:10px 14px">${fieldsHtml}</div>` : ''}
    <div style="padding:8px 14px;background:#fafafa;border-top:1px solid #f0f0f0">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:11px;color:#999">Reference ID</span>
        <span style="font-size:11px;font-family:monospace;font-weight:500;color:#2d6a4f">${displayId}</span>
      </div>
      <div style="font-size:10px;color:#aaa;margin-top:2px">
        ${status === 'duplicate' ? (dupHints[lang] || dupHints.en) : (refHints[lang] || refHints.en)}
      </div>
    </div>`;
  return card;
}

// ── Event listeners ───────────────────────────────────────────────────────────
attachBtn.addEventListener('click', () => { if (!state.sessionEnded) fileInput.click(); });

fileInput.addEventListener('change', e => {
  const file = e.target.files?.[0];
  if (file) processDocument(file);
  fileInput.value = '';
});

sendBtn.addEventListener('click', () => {
  const text = textInput.value.trim();
  if (!text) return;
  textInput.value = '';
  handleTextInput(text);
});

textInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const text = textInput.value.trim();
    if (!text) return;
    textInput.value = '';
    handleTextInput(text);
  }
});

muteBtn.addEventListener('click', () => {
  state.muted = !state.muted;
  muteBtn.textContent = state.muted ? '🔇' : '🔊';
  muteBtn.classList.toggle('muted', state.muted);
  if (state.muted) window.speechSynthesis.cancel();
});

resetBtn.addEventListener('click', () => {
  clearTimeout(inactivityTimer);
  clearTimeout(warnTimer);
  clearTimeout(expireTimer);
  state = { lang: null, docType: null, step: 'lang_select', processing: false, muted: state.muted, inactive: false, sessionEnded: false };
  chatWindow.innerHTML = '';
  textInput.disabled = false;
  textInput.value = '';
  sendBtn.disabled = false;
  attachBtn.style.display = 'none';
  textInput.placeholder = 'Type a message…';
  statusDot.className = 'status-dot online';
  statusText.textContent = 'Online';
  hideBanner();
  hideProgress();
  startLangSelect();
  resetInactivityTimer();
});

chatWindow.addEventListener('dragover', e => { e.preventDefault(); chatWindow.style.background = '#edfdf3'; });
chatWindow.addEventListener('dragleave', () => { chatWindow.style.background = ''; });
chatWindow.addEventListener('drop', e => {
  e.preventDefault(); chatWindow.style.background = '';
  const file = e.dataTransfer.files?.[0];
  if (file && state.step === 'upload') processDocument(file);
});

// ── Init ──────────────────────────────────────────────────────────────────────
startLangSelect();
resetInactivityTimer();
