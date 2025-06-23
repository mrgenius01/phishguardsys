document.addEventListener('DOMContentLoaded', function() {
const emailList = document.getElementById('email-list');
const emailView = document.getElementById('email-view');
const emailSubject = document.getElementById('email-subject');
const emailBody = document.getElementById('email-body');
const emailSender = document.getElementById('email-sender');
const emailTime = document.getElementById('email-time');
const emailAvatar = document.getElementById('email-avatar');
const analyzeBtn = document.getElementById('analyze-btn');
const analysisResult = document.getElementById('analysis-result');
const assistantTip = document.getElementById('assistant-tip');
const featureDetails = document.getElementById('feature-details');
const backBtn = document.getElementById('back-btn');

let selectedEmail = null;
let selectedIdx = null;
let demoEmails = [];
let emailAnalyses = [];
let loadingEmailIdx = null;
let isFetchingEmails = false;
let lastAnalysis = null;

// Tag logic
function getTagAndClass(analysis) {
  if (!analysis || !analysis.prediction) return { tag: 'Unknown', cls: 'tag-unknown' };
  if (analysis.prediction === 0) return { tag: 'Clean', cls: 'tag-clean' };
  if (analysis.prediction === 1 && analysis.features && analysis.features.gpt_score > 0.8) return { tag: 'Spam', cls: 'tag-spam' };
  if (analysis.prediction === 1) return { tag: 'Potential Scam', cls: 'tag-scam' };
  return { tag: 'Unknown', cls: 'tag-unknown' };
}

// Fetch emails from backend
async function fetchEmailsFromServer() {
  isFetchingEmails = true;
  renderInbox();
  try {
    const res = await fetch('/fetch_emails');
    const data = await res.json();
    if (data.emails) {
      demoEmails = data.emails;
      emailAnalyses = Array(demoEmails.length).fill(null);
      isFetchingEmails = false;
      renderInbox();
      analyzeAllEmails();
    } else {
      // fallback to demo emails if error
      demoEmails = [
        {
          sender: "alerts@scam.link",
          subject: "Win a free iPhone!",
          body: "Congratulations, click here to claim your prize: http://scam.link",
          received: "2025-06-18 09:12"
        },
        {
          sender: "billing@company.com",
          subject: "Invoice attached",
          body: "Please see the attached invoice for your records.",
          received: "2025-06-18 08:45"
        },
        {
          sender: "security@fakebank.com",
          subject: "Urgent: Account Suspended",
          body: "Your account has been suspended. Visit http://fakebank.com to reactivate.",
          received: "2025-06-17 22:10"
        },
        {
          sender: "hr@company.com",
          subject: "Team Meeting Update",
          body: "The meeting is rescheduled to Friday at 10am.",
          received: "2025-06-17 17:30"
        },
        {
          sender: "support@secure-reset.com",
          subject: "Password Reset",
          body: "Reset your password at http://secure-reset.com",
          received: "2025-06-17 15:05"
        },
        {
          sender: "colleague@company.com",
          subject: "Lunch plans",
          body: "Are you free for lunch tomorrow?",
          received: "2025-06-17 12:00"
        }
      ];
      emailAnalyses = Array(demoEmails.length).fill(null);
      isFetchingEmails = false;
      renderInbox();
      analyzeAllEmails();
    }
  } catch (e) {
    // fallback to demo emails if error
    demoEmails = [
      {
        sender: "alerts@scam.link",
        subject: "Win a free iPhone!",
        body: "Congratulations, click here to claim your prize: http://scam.link",
        received: "2025-06-18 09:12"
      },
      {
        sender: "billing@company.com",
        subject: "Invoice attached",
        body: "Please see the attached invoice for your records.",
        received: "2025-06-18 08:45"
      },
      {
        sender: "security@fakebank.com",
        subject: "Urgent: Account Suspended",
        body: "Your account has been suspended. Visit http://fakebank.com to reactivate.",
        received: "2025-06-17 22:10"
      },
      {
        sender: "hr@company.com",
        subject: "Team Meeting Update",
        body: "The meeting is rescheduled to Friday at 10am.",
        received: "2025-06-17 17:30"
      },
      {
        sender: "support@secure-reset.com",
        subject: "Password Reset",
        body: "Reset your password at http://secure-reset.com",
        received: "2025-06-17 15:05"
      },
      {
        sender: "colleague@company.com",
        subject: "Lunch plans",
        body: "Are you free for lunch tomorrow?",
        received: "2025-06-17 12:00"
      }
    ];
    emailAnalyses = Array(demoEmails.length).fill(null);
    isFetchingEmails = false;
    renderInbox();
    analyzeAllEmails();
  }
}

// Settings form logic
const settingsForm = document.getElementById('settings-form');
settingsForm.onsubmit = async function(e) {
  e.preventDefault();
  const config = {
    email: document.getElementById('config-email').value,
    imap_server: document.getElementById('config-imap-server').value,
    imap_port: document.getElementById('config-imap-port').value,
    password: document.getElementById('config-password').value
  };
  await fetch('/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  alert('Settings saved!');
  settingsView.style.display = 'none';
  fetchEmailsFromServer();
};

// Load config to prefill settings form
async function loadConfig() {
  const res = await fetch('/config');
  const cfg = await res.json();
  if (cfg) {
    document.getElementById('config-email').value = cfg.email || '';
    document.getElementById('config-imap-server').value = cfg.imap_server || '';
    document.getElementById('config-imap-port').value = cfg.imap_port || 993;
    document.getElementById('config-password').value = cfg.password || '';
  }
}

function getInitials(sender) {
  if (!sender) return '';
  const parts = sender.split('@')[0].split('.');
  if (parts.length > 1) return (parts[0][0] + parts[1][0]).toUpperCase();
  return sender[0].toUpperCase();
}

async function analyzeAllEmails() {
  for (let i = 0; i < demoEmails.length; i++) {
    loadingEmailIdx = i;
    renderInbox();
    const payload = { ...demoEmails[i], sender: demoEmails[i].sender };
    try {
      const res = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      emailAnalyses[i] = data;
      loadingEmailIdx = null;
      renderInbox();
    } catch (e) {
      emailAnalyses[i] = null;
      loadingEmailIdx = null;
      renderInbox();
    }
  }
  loadingEmailIdx = null;
  renderInbox();
}

function renderInbox() {
  emailList.innerHTML = '';
  if (isFetchingEmails) {
    const li = document.createElement('li');
    li.className = 'email-item';
    li.innerHTML = '<div style="width:100%;text-align:center;padding:32px 0;color:#4f8cff;font-size:1.1rem;">Loading emails from server...</div>';
    emailList.appendChild(li);
    emailView.style.display = 'none';
    emailList.parentElement.style.display = 'block';
    return;
  }
  demoEmails.forEach((email, idx) => {
    const li = document.createElement('li');
    li.className = 'email-item' + (selectedIdx === idx ? ' selected' : '');
    li.onclick = () => showEmail(idx);
    let tagHtml = '';
    if (loadingEmailIdx === idx) {
      tagHtml = `<span class="tag tag-unknown">Loading analysis for {${email.sender || idx}}</span>`;
    } else {
      tagHtml = `<span class="tag ${(emailAnalyses[idx] ? getTagAndClass(emailAnalyses[idx]).cls : 'tag-unknown')}">
        ${(emailAnalyses[idx] ? getTagAndClass(emailAnalyses[idx]).tag : 'Analyzing...')}
      </span>`;
    }
    li.innerHTML = `
      <div class="email-avatar">${getInitials(email.sender)}</div>
      <div class="email-info">
        <div class="email-sender">${email.sender}</div>
        <div class="email-subject">${email.subject}</div>
        <div class="email-preview">${email.body.slice(0, 40)}${email.body.length > 40 ? '...' : ''}</div>
      </div>
      <div class="email-time">${email.received}</div>
      ${tagHtml}
      <span class="info-icon" data-idx="${idx}" style="cursor:pointer; color:#4f8cff; margin-left:6px;">ℹ️</span>
    `;
    emailList.appendChild(li);
  });
  emailView.style.display = 'none';
  emailList.parentElement.style.display = 'block';
  // Add info icon listeners
  document.querySelectorAll('.info-icon').forEach(icon => {
    icon.onclick = function(e) {
      e.stopPropagation();
      const idx = parseInt(icon.getAttribute('data-idx'));
      showAnalysisModal(idx);
    };
  });
}

function showEmail(idx) {
  selectedEmail = demoEmails[idx];
  selectedIdx = idx;
  emailSender.textContent = selectedEmail.sender;
  emailTime.textContent = selectedEmail.received;
  emailSubject.textContent = selectedEmail.subject;
  emailBody.textContent = selectedEmail.body;
  if (emailAvatar) {
    emailAvatar.textContent = getInitials(selectedEmail.sender);
  }
  analysisResult.style.display = 'none';
  emailView.style.display = 'block';
  emailList.parentElement.style.display = 'none';
  // Hide analyze button, show submit button
  if (analyzeBtn) analyzeBtn.style.display = 'none';
  if (submitBtn) submitBtn.style.display = 'inline-block';
  lastAnalysis = emailAnalyses[idx];
  // Show user-friendly GPT explanation
  showUserAnalysisReport(selectedEmail, lastAnalysis);
}

async function showUserAnalysisReport(email, analysis) {
  const tipDiv = document.getElementById('assistant-tip');
  const detailsPre = document.getElementById('feature-details');
  if (!analysis) {
    tipDiv.textContent = 'No analysis available.';
    detailsPre.textContent = '';
    return;
  }
  tipDiv.textContent = 'Loading friendly explanation...';
  detailsPre.textContent = '';
  try {
    const res = await fetch('/user_gpt_explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, analysis })
    });
    const data = await res.json();
    tipDiv.textContent = data.friendly_explanation || 'No explanation.';
    detailsPre.textContent = '';
  } catch (e) {
    tipDiv.textContent = 'Could not load explanation.';
    detailsPre.textContent = '';
  }
}

function showAnalysisModal(idx) {
  const modal = document.getElementById('analysis-modal');
  const tip = document.getElementById('modal-analysis-tip');
  const details = document.getElementById('modal-feature-details');
  const analysis = emailAnalyses[idx];
  if (analysis) {
    tip.textContent = analysis.explanation;
    details.textContent = JSON.stringify(analysis.features, null, 2);
  } else {
    tip.textContent = 'No analysis available.';
    details.textContent = '';
  }
  modal.style.display = 'flex';
}

document.getElementById('close-modal').onclick = function() {
  document.getElementById('analysis-modal').style.display = 'none';
};

// Settings screen logic
const settingsLink = document.getElementById('settings-link');
const settingsView = document.getElementById('settings-view');
const inboxList = document.getElementById('inbox-list');
settingsLink.onclick = function() {
  inboxList.style.display = 'none';
  emailView.style.display = 'none';
  settingsView.style.display = 'block';
};
document.getElementById('back-btn').onclick = function() {
  selectedIdx = null;
  settingsView.style.display = 'none';
  renderInbox();
};

backBtn.onclick = function() {
  selectedIdx = null;
  renderInbox();
};

// Add submit to IT button logic
let submitBtn = document.getElementById('submit-it-btn');
if (!submitBtn) {
  submitBtn = document.createElement('button');
  submitBtn.id = 'submit-it-btn';
  submitBtn.textContent = 'Submit to IT Support';
  submitBtn.style.marginLeft = '16px';
  submitBtn.style.display = 'none';
  analyzeBtn.parentNode.insertBefore(submitBtn, analyzeBtn.nextSibling);
}
submitBtn.onclick = async function() {
  if (!selectedEmail || !lastAnalysis) return;
  const payload = { ...selectedEmail, analysis: lastAnalysis };
  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting...';
  try {
    await fetch('/submit_it_review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    submitBtn.textContent = 'Submitted!';
    setTimeout(() => {
      submitBtn.textContent = 'Submit to IT Support';
      submitBtn.disabled = false;
    }, 2000);
  } catch (e) {
    submitBtn.textContent = 'Error! Try again';
    setTimeout(() => {
      submitBtn.textContent = 'Submit to IT Support';
      submitBtn.disabled = false;
    }, 2000);
  }
};

// Initial load
loadConfig();
fetchEmailsFromServer();
});
