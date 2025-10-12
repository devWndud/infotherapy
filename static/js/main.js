function toggleNav() {
  const nav = document.getElementById('site-nav');
  const navToggle = document.querySelector('.nav-toggle');
  
  if (!nav || !navToggle) {
    console.log('Navigation elements not found');
    return;
  }
  
  console.log('Toggle nav called');
  nav.classList.toggle('open');
  
  if (nav.classList.contains('open')) {
    document.body.style.overflow = 'hidden';
    navToggle.setAttribute('aria-expanded', 'true');
    console.log('Menu opened');
  } else {
    document.body.style.overflow = '';
    navToggle.setAttribute('aria-expanded', 'false');
    console.log('Menu closed');
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
  const navToggle = document.querySelector('.nav-toggle');
  
  if (navToggle) {
    let touchStartTime = 0;
    let touchEndTime = 0;
    let isTouchHandled = false;
    
    function handleToggle(e) {
      if (isTouchHandled) return;
      isTouchHandled = true;
      
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      
      console.log('Toggle triggered by:', e.type);
      toggleNav();
      
      setTimeout(() => {
        isTouchHandled = false;
      }, 300);
      
      return false;
    }
    
    navToggle.addEventListener('touchstart', function(e) {
      touchStartTime = Date.now();
      console.log('Touch start at:', touchStartTime);
    }, { passive: true });
    
    navToggle.addEventListener('touchend', function(e) {
      touchEndTime = Date.now();
      const touchDuration = touchEndTime - touchStartTime;
      
      console.log('Touch end at:', touchEndTime, 'Duration:', touchDuration, 'Handled:', isTouchHandled);
      
      if (touchDuration < 500 && !isTouchHandled) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Processing touch end');
        handleToggle(e);
      }
    }, { passive: false });
    
    navToggle.addEventListener('touchcancel', function(e) {
      console.log('Touch cancelled');
      isTouchHandled = false;
    }, { passive: true });
    
    navToggle.addEventListener('click', handleToggle, { passive: false });
    navToggle.addEventListener('mousedown', handleToggle, { passive: false });
    
    navToggle.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleToggle(e);
      }
    });
    
    navToggle.setAttribute('tabindex', '0');
    navToggle.setAttribute('role', 'button');
    navToggle.style.pointerEvents = 'auto';
    navToggle.style.cursor = 'pointer';
    navToggle.style.touchAction = 'manipulation';
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


