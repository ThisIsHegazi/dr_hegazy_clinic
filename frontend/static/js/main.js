const apiUrl = window.apiUrl || function (path) { return path; };
const hasBackend =
  Boolean((window.API_BASE_URL || '').trim()) ||
  (location.protocol !== 'file:' && location.protocol !== 'about:');

function backendWarningHtml() {
  return [
    '<span style="font-size:32px">⚠️</span>',
    '<p>الواجهة تعمل بدون اتصال بالخادم.</p>',
    '<p style="font-size:13px;color:var(--text-muted)">شغّل السيرفر أو اضبط <span dir="ltr">API_BASE_URL</span>.</p>'
  ].join('');
}

// ===== ARABIC HELPERS =====
function formatSlotTime(isoString) {
  const d = new Date(isoString);
  return new Intl.DateTimeFormat('ar-EG', {
    timeZone: 'Africa/Cairo',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).format(d);
}

function formatSlotFull(isoString) {
  const d = new Date(isoString);
  const day = new Intl.DateTimeFormat('ar-EG', { timeZone: 'Africa/Cairo', weekday: 'long' }).format(d);
  const dateStr = new Intl.DateTimeFormat('ar-EG', { timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
  const time = formatSlotTime(isoString);
  return `${day} ${dateStr} — ${time}`;
}

function formatDayHeader(dateStr) {
  const d = new Date(dateStr + 'T12:00:00+02:00');
  const name = new Intl.DateTimeFormat('ar-EG', { timeZone: 'Africa/Cairo', weekday: 'long' }).format(d);
  const full = new Intl.DateTimeFormat('ar-EG', { timeZone: 'Africa/Cairo', day: 'numeric', month: 'long' }).format(d);
  return { name, full };
}

function formatDate(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('ar-EG', {
      timeZone: 'Africa/Cairo',
      weekday: 'long', year: 'numeric', month: 'long',
      day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  } catch { return isoString; }
}

// ===== TABS =====
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + target).classList.add('active');
    hideResponse();
  });
});

// ===== RESPONSE BOX =====
function showResponse(type, html) {
  const box = document.getElementById('responseBox');
  box.className = 'response-box ' + type;
  box.innerHTML = html;
  box.style.display = 'block';
}

function hideResponse() {
  const box = document.getElementById('responseBox');
  box.style.display = 'none';
}

// ===== FIELD VALIDATION =====
function clearErrors() {
  document.querySelectorAll('.field-error').forEach(el => el.textContent = '');
  document.querySelectorAll('input.error').forEach(el => el.classList.remove('error'));
}

function setError(inputId, errorId, message) {
  const input = document.getElementById(inputId);
  const error = document.getElementById(errorId);
  if (input) input.classList.add('error');
  if (error) error.textContent = message;
}

function validateBook() {
  clearErrors();
  const name = document.getElementById('name').value.trim();
  const phone = document.getElementById('phone').value.trim();
  let valid = true;
  if (!name) { setError('name', 'nameError', 'الرجاء إدخال الاسم الكامل'); valid = false; }
  if (!phone) { setError('phone', 'phoneError', 'الرجاء إدخال رقم الهاتف'); valid = false; }
  return valid;
}

function validateCancel() {
  clearErrors();
  const phone = document.getElementById('cancelPhone').value.trim();
  if (!phone) { setError('cancelPhone', 'cancelPhoneError', 'الرجاء إدخال رقم الهاتف'); return false; }
  return true;
}

function validateInquiry() {
  clearErrors();
  const phone = document.getElementById('inquiryPhone').value.trim();
  if (!phone) { setError('inquiryPhone', 'inquiryPhoneError', 'الرجاء إدخال رقم الهاتف'); return false; }
  return true;
}

// ===== LOADING STATE =====
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  const text = btn.querySelector('.btn-text');
  const spinner = btn.querySelector('.btn-spinner');
  btn.disabled = loading;
  text.style.display = loading ? 'none' : '';
  spinner.style.display = loading ? '' : 'none';
}

// ===== SLOT ACCORDION =====
let selectedSlot = null;

async function loadSlots() {
  const loading = document.getElementById('slotLoading');
  if (!loading) return;
  const noSlots = document.getElementById('noSlots');
  const accordion = document.getElementById('slotAccordion');

  loading.style.display = 'flex';
  noSlots.style.display = 'none';
  accordion.style.display = 'none';
  accordion.innerHTML = '';

  if (!hasBackend) {
    loading.style.display = 'none';
    noSlots.style.display = 'flex';
    noSlots.innerHTML = backendWarningHtml();
    return;
  }

  try {
    const res = await fetch(apiUrl('/appointments/slots?days=5'));
    if (!res.ok) throw new Error('Server error');
    const data = await res.json();
    const days = data.days || [];

    loading.style.display = 'none';

    if (!days.length) {
      noSlots.style.display = 'flex';
      return;
    }

    days.forEach((day, idx) => {
      const { name, full } = formatDayHeader(day.date);
      const slotCount = day.slots.length;

      const dayEl = document.createElement('div');
      dayEl.className = 'slot-day' + (idx === 0 ? ' open' : '');
      dayEl.innerHTML = `
        <button class="slot-day-header" type="button" aria-expanded="${idx === 0}">
          <div class="slot-day-info">
            <span class="slot-day-name">${name}</span>
            <span class="slot-day-date">${full}</span>
          </div>
          <span class="slot-day-count">${slotCount} موعد متاح</span>
          <span class="slot-day-arrow">▼</span>
        </button>
        <div class="slot-times-panel">
          <div class="slot-times-grid"></div>
        </div>
      `;

      const header = dayEl.querySelector('.slot-day-header');
      header.addEventListener('click', () => {
        const isOpen = dayEl.classList.contains('open');
        dayEl.classList.toggle('open', !isOpen);
        header.setAttribute('aria-expanded', String(!isOpen));
      });

      const grid = dayEl.querySelector('.slot-times-grid');
      day.slots.forEach(slotIso => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'slot-time';
        btn.textContent = formatSlotTime(slotIso);
        btn.dataset.iso = slotIso;
        if (selectedSlot === slotIso) btn.classList.add('selected');
        btn.addEventListener('click', () => selectSlot(slotIso, btn));
        grid.appendChild(btn);
      });

      accordion.appendChild(dayEl);
    });

    accordion.style.display = 'flex';
  } catch (err) {
    loading.style.display = 'none';
    noSlots.style.display = 'flex';
    noSlots.innerHTML = '<span style="font-size:32px">⚠️</span><p>تعذّر تحميل المواعيد. تحقق من اتصالك.</p>';
  }
}

function selectSlot(isoString, btnEl) {
  selectedSlot = isoString;

  document.querySelectorAll('.slot-time').forEach(b => b.classList.remove('selected'));
  if (btnEl) btnEl.classList.add('selected');

  document.getElementById('selectedSlotLabel').textContent = formatSlotFull(isoString);
  const details = document.getElementById('stepDetails');
  details.style.display = 'block';
  details.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

if (document.getElementById('changeSlotBtn')) {
document.getElementById('changeSlotBtn').addEventListener('click', () => {
  selectedSlot = null;
  document.querySelectorAll('.slot-time').forEach(b => b.classList.remove('selected'));
  document.getElementById('stepDetails').style.display = 'none';
  hideResponse();
});
}

loadSlots();

// ===== SUGGESTED DATE MODAL =====
let pendingBookingData = null;

function showSuggestModal(message, suggestedDate, originalData) {
  pendingBookingData = { data: originalData, suggestedDate };
  document.getElementById('suggestMsg').innerHTML =
    `هذا الموعد لم يعد متاحاً.<br/>أقرب موعد متاح هو: <strong>${formatDate(suggestedDate)}</strong><br/>هل تريد تأكيد الحجز في هذا الموعد؟`;
  document.getElementById('suggestModal').style.display = 'flex';
}

function hideSuggestModal() {
  document.getElementById('suggestModal').style.display = 'none';
  pendingBookingData = null;
}

if (document.getElementById('acceptBtn')) {
document.getElementById('acceptBtn').addEventListener('click', async () => {
  if (!pendingBookingData) return;
  hideSuggestModal();
  await submitBooking(pendingBookingData.data, true, null);
});

document.getElementById('declineBtn').addEventListener('click', () => {
  hideSuggestModal();
  showResponse('info', '<span class="response-icon">ℹ️</span> تم رفض الموعد المقترح. يمكنك اختيار موعد آخر.');
  loadSlots();
});

const suggestModal = document.getElementById('suggestModal');
if (suggestModal) {
  suggestModal.addEventListener('click', (e) => {
    if (e.target === suggestModal) hideSuggestModal();
  });
}
}

// ===== BOOK FORM =====
if (document.getElementById('bookForm')) {
document.getElementById('bookForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateBook()) return;
  const data = {
    name: document.getElementById('name').value.trim(),
    phone_number: document.getElementById('phone').value.trim(),
  };
  await submitBooking(data, false, selectedSlot);
});
}

async function submitBooking(data, acceptSuggested, preferredSlot) {
  if (!hasBackend) {
    showResponse('info', '<span class="response-icon">ℹ️</span> الخادم غير متصل. شغّل السيرفر أو اضبط <span dir="ltr">API_BASE_URL</span>.');
    return;
  }

  setLoading('bookBtn', true);
  hideResponse();

  try {
    let url = `/appointments?accept_suggested=${acceptSuggested}`;
    if (preferredSlot) url += `&preferred_slot=${encodeURIComponent(preferredSlot)}`;

    const res = await fetch(apiUrl(url), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    const json = await res.json();

    if (res.ok) {
      const msg = json.message || 'تم الحجز بنجاح';
      showResponse('success', `<span class="response-icon">✅</span> <strong>${msg}</strong>`);
      document.getElementById('bookForm').reset();
      selectedSlot = null;
      document.getElementById('stepDetails').style.display = 'none';
      loadSlots();
    } else if (res.status === 409) {
      const detail = json.detail || {};
      const message = detail.message || '';
      const suggestedDate = detail.suggested_date || null;
      if (suggestedDate) {
        showSuggestModal(message, suggestedDate, data);
      } else {
        showResponse('warning', `<span class="response-icon">⚠️</span> <strong>${message}</strong>`);
      }
    } else {
      const msg = (json.detail && json.detail.message) || json.detail || 'حدث خطأ، يرجى المحاولة مرة أخرى.';
      showResponse('error', `<span class="response-icon">❌</span> ${msg}`);
    }
  } catch (err) {
    showResponse('error', '<span class="response-icon">❌</span> تعذّر الاتصال بالخادم. تحقق من اتصالك بالإنترنت.');
  } finally {
    setLoading('bookBtn', false);
  }
}

// ===== INQUIRY FORM =====
if (document.getElementById('inquiryForm')) {
document.getElementById('inquiryForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateInquiry()) return;

  const phone = document.getElementById('inquiryPhone').value.trim();
  setLoading('inquiryBtn', true);
  const resultBox = document.getElementById('inquiryResult');
  resultBox.style.display = 'none';
  resultBox.innerHTML = '';

  if (!hasBackend) {
    resultBox.innerHTML = `<div class="inquiry-card not-found"><div class="inquiry-header"><span>ℹ️</span><span>الخادم غير متصل</span></div><p style="font-size:14px;color:var(--text-muted);margin:0">شغّل السيرفر أو اضبط <span dir="ltr">API_BASE_URL</span>.</p></div>`;
    resultBox.style.display = 'block';
    setLoading('inquiryBtn', false);
    return;
  }

  try {
    const res = await fetch(apiUrl(`/appointments/check/${encodeURIComponent(phone)}`));
    const json = await res.json();

    if (res.ok) {
      const isCompleted = json.completed;
      const badgeClass = isCompleted ? 'done' : 'active';
      const badgeText = isCompleted ? 'مكتمل' : 'مؤكد ✓';
      const cardClass = isCompleted ? 'completed' : '';
      const icon = isCompleted ? '📋' : '✅';
      const title = isCompleted ? 'موعد مكتمل' : 'موعدك مؤكد';

      resultBox.innerHTML = `
        <div class="inquiry-card ${cardClass}">
          <div class="inquiry-header">
            <span class="inquiry-header-icon">${icon}</span>
            <span>${title}</span>
          </div>
          <div class="inquiry-rows">
            <div class="inquiry-row">
              <span class="inquiry-row-label">الاسم:</span>
              <span class="inquiry-row-value">${json.name || '—'}</span>
            </div>
            <div class="inquiry-row">
              <span class="inquiry-row-label">الهاتف:</span>
              <span class="inquiry-row-value" dir="ltr">${json.phone_number || '—'}</span>
            </div>
            <div class="inquiry-row">
              <span class="inquiry-row-label">الموعد:</span>
              <span class="inquiry-row-value">${json.scheduled_at_label || formatDate(json.scheduled_at) || '—'}</span>
            </div>
            <div class="inquiry-row">
              <span class="inquiry-row-label">الحالة:</span>
              <span class="inquiry-row-value"><span class="inquiry-badge ${badgeClass}">${badgeText}</span></span>
            </div>
          </div>
        </div>
      `;
    } else if (res.status === 404) {
      resultBox.innerHTML = `
        <div class="inquiry-card not-found">
          <div class="inquiry-header">
            <span class="inquiry-header-icon">❌</span>
            <span>لا يوجد موعد</span>
          </div>
          <p style="font-size:14px;color:var(--danger);margin:0">لا يوجد أي موعد مسجل لهذا الرقم.</p>
        </div>
      `;
    } else {
      const msg = (json.detail && json.detail.message) || 'حدث خطأ. يرجى المحاولة مرة أخرى.';
      resultBox.innerHTML = `<div class="inquiry-card not-found"><div class="inquiry-header"><span>⚠️</span><span>خطأ</span></div><p style="font-size:14px;color:var(--danger);margin:0">${msg}</p></div>`;
    }

    resultBox.style.display = 'block';
  } catch (err) {
    resultBox.innerHTML = `<div class="inquiry-card not-found"><div class="inquiry-header"><span>⚠️</span><span>خطأ في الاتصال</span></div><p style="font-size:14px;color:var(--danger);margin:0">تعذّر الاتصال بالخادم. تحقق من اتصالك.</p></div>`;
    resultBox.style.display = 'block';
  } finally {
    setLoading('inquiryBtn', false);
  }
});
}

// ===== CANCEL FORM =====
if (document.getElementById('cancelForm')) {
document.getElementById('cancelForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!validateCancel()) return;

  const phone = document.getElementById('cancelPhone').value.trim();
  setLoading('cancelBtn', true);
  hideResponse();

  if (!hasBackend) {
    showResponse('info', '<span class="response-icon">ℹ️</span> الخادم غير متصل. شغّل السيرفر أو اضبط <span dir="ltr">API_BASE_URL</span>.');
    setLoading('cancelBtn', false);
    return;
  }

  try {
    const res = await fetch(apiUrl(`/appointments/${encodeURIComponent(phone)}`), { method: 'DELETE' });
    const json = await res.json();

    if (res.ok) {
      const msg = json.message || 'تم إلغاء الموعد';
      showResponse('success', `<span class="response-icon">✅</span> <strong>${msg}</strong>`);
      document.getElementById('cancelForm').reset();
      loadSlots();
    } else if (res.status === 404) {
      const msg = (json.detail && json.detail.message) || 'لا يوجد موعد مسجل لهذا الرقم.';
      showResponse('error', `<span class="response-icon">❌</span> ${msg}`);
    } else if (res.status === 409) {
      const msg = (json.detail && json.detail.message) || 'الموعد مكتمل ولا يمكن إلغاؤه.';
      showResponse('warning', `<span class="response-icon">⚠️</span> ${msg}`);
    } else {
      const msg = (json.detail && json.detail.message) || json.detail || 'حدث خطأ، يرجى المحاولة مرة أخرى.';
      showResponse('error', `<span class="response-icon">❌</span> ${msg}`);
    }
  } catch (err) {
    showResponse('error', '<span class="response-icon">❌</span> تعذّر الاتصال بالخادم. تحقق من اتصالك بالإنترنت.');
  } finally {
    setLoading('cancelBtn', false);
  }
});
}

// ===== NAVBAR SCROLL EFFECT =====
window.addEventListener('scroll', () => {
  const navbar = document.querySelector('.navbar');
  if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 20);
});
