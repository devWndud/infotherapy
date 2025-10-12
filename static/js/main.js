function toggleNav() {
  const nav = document.getElementById('site-nav');
  const navToggle = document.querySelector('.nav-toggle');
  
  if (!nav || !navToggle) return;
  
  nav.classList.toggle('open');
  
  // 모바일에서 메뉴 열릴 때 body 스크롤 방지
  if (nav.classList.contains('open')) {
    document.body.style.overflow = 'hidden';
    navToggle.setAttribute('aria-expanded', 'true');
  } else {
    document.body.style.overflow = '';
    navToggle.setAttribute('aria-expanded', 'false');
  }
}

// 모바일 메뉴 외부 클릭 시 닫기
document.addEventListener('click', (e) => {
  const nav = document.getElementById('site-nav');
  const navToggle = document.querySelector('.nav-toggle');
  
  if (nav && nav.classList.contains('open')) {
    if (!nav.contains(e.target) && !navToggle.contains(e.target)) {
      nav.classList.remove('open');
      document.body.style.overflow = '';
    }
  }
});

// ESC 키로 모바일 메뉴 닫기
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const nav = document.getElementById('site-nav');
    if (nav && nav.classList.contains('open')) {
      nav.classList.remove('open');
      document.body.style.overflow = '';
    }
  }
});

// 모바일 메뉴 링크 클릭 시 자동으로 메뉴 닫기
document.addEventListener('DOMContentLoaded', () => {
  const navLinks = document.querySelectorAll('.nav-content a');
  const navToggle = document.querySelector('.nav-toggle');
  
  // 햄버거 버튼 이벤트 리스너 추가
  if (navToggle) {
    navToggle.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleNav();
    });
  }
  
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      const nav = document.getElementById('site-nav');
      if (nav && nav.classList.contains('open')) {
        nav.classList.remove('open');
        document.body.style.overflow = '';
        if (navToggle) {
          navToggle.setAttribute('aria-expanded', 'false');
        }
      }
    });
  });
});

// Simple client-side helpers for forms (UI only)
function setLoading(button, isLoading) {
  if (!button) return;
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = '처리 중...';
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || '제출';
    button.disabled = false;
  }
}

// Learn page category filter
document.addEventListener('DOMContentLoaded', () => {
  // tabs removed; use multi-category picker once

  // Multi-category picker
  const picker = null; // modal removed; use toggle buttons
  const cancelBtn = null;
  const form = null;
  const filterBar = document.getElementById('cat-toggle');

  const applyMulti = (cats) => {
    const lists = [document.getElementById('materials'), document.getElementById('assignments')];
    lists.forEach(list => {
      if (!list) return;
      list.querySelectorAll('.list-item').forEach(item => {
        const c = item.getAttribute('data-category');
        const show = !cats.length || cats.includes(c);
        item.style.display = show ? '' : 'none';
      });
    });
    // update persistent chip states
    if (filterBar) {
      filterBar.style.display = 'flex';
      filterBar.querySelectorAll('.chip').forEach(b => b.classList.toggle('active', cats.includes(b.dataset.cat)));
    }
  };

  const stored = localStorage.getItem('cats');
  let selectedCats = stored ? stored.split(',').filter(Boolean) : [];
  if (!stored) {
    // default: all on (including web)
    selectedCats = ['unity','ml','dl','web'];
    localStorage.setItem('cats', selectedCats.join(','));
  }
  applyMulti(selectedCats);

  // no manual open; only first-visit modal
  if (cancelBtn && picker) {
    cancelBtn.addEventListener('click', () => picker.classList.remove('show'));
  }
  // Toggle buttons for categories
  if (filterBar) {
    // initialize states
    filterBar.querySelectorAll('.chip').forEach(btn => btn.classList.toggle('active', selectedCats.includes(btn.dataset.cat)));
    filterBar.addEventListener('click', (e) => {
      const btn = e.target.closest('.chip');
      if (!btn) return;
      const cat = btn.dataset.cat;
      if (selectedCats.includes(cat)) {
        if (selectedCats.length === 1) return; // 최소 1개 유지
        selectedCats = selectedCats.filter(c => c !== cat);
      } else {
        selectedCats.push(cat);
      }
      localStorage.setItem('cats', selectedCats.join(','));
      applyMulti(selectedCats);
    });
  }
});


