function toggleNav() {
  const nav = document.querySelector('.nav');
  if (nav) {
    nav.classList.toggle('open');
    if (nav.classList.contains('open')) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
  }
}

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

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const nav = document.getElementById('site-nav');
    if (nav && nav.classList.contains('open')) {
      nav.classList.remove('open');
      document.body.style.overflow = '';
    }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const navLinks = document.querySelectorAll('.nav-content a');
  
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

document.addEventListener('DOMContentLoaded', () => {
  const picker = null;
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
    if (filterBar) {
      filterBar.style.display = 'flex';
      filterBar.querySelectorAll('.chip').forEach(b => b.classList.toggle('active', cats.includes(b.dataset.cat)));
    }
  };

  const stored = localStorage.getItem('cats');
  let selectedCats = stored ? stored.split(',').filter(Boolean) : [];
  if (!stored) {
    selectedCats = ['unity','ml','dl','web'];
    localStorage.setItem('cats', selectedCats.join(','));
  }
  applyMulti(selectedCats);

  if (cancelBtn && picker) {
    cancelBtn.addEventListener('click', () => picker.classList.remove('show'));
  }
  if (filterBar) {
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


