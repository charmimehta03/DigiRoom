// Toggle password visibility
function togglePassword() {
  const input = document.getElementById('password');
  const btn = document.querySelector('.toggle-pw');
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁️';
  }
}

// 3D Card Tilt
const card = document.querySelector('.card');
const rightPanel = document.querySelector('.right-panel');

if (window.matchMedia('(pointer: fine)').matches) {
  rightPanel.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / window.innerWidth;
    const dy = (e.clientY - cy) / window.innerHeight;
    card.style.transform = `perspective(900px) rotateY(${dx * 5}deg) rotateX(${-dy * 5}deg)`;
  });

  rightPanel.addEventListener('mouseleave', () => {
    card.style.transition = 'transform 0.5s ease';
    card.style.transform = 'perspective(900px) rotateY(0deg) rotateX(0deg)';
  });

  rightPanel.addEventListener('mouseenter', () => {
    card.style.transition = 'transform 0.12s ease';
  });
}

// Ripple on submit button
const rippleStyle = document.createElement('style');
rippleStyle.textContent = `@keyframes ripple { to { transform: scale(40); opacity: 0; } }`;
document.head.appendChild(rippleStyle);

document.querySelector('.btn-submit').addEventListener('click', function(e) {
  const ripple = document.createElement('span');
  const rect = this.getBoundingClientRect();
  ripple.style.cssText = `
    position:absolute; border-radius:50%; background:rgba(255,255,255,0.18);
    width:10px; height:10px;
    left:${e.clientX - rect.left - 5}px; top:${e.clientY - rect.top - 5}px;
    transform:scale(0); animation:ripple 0.5s ease forwards; pointer-events:none;
  `;
  this.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
});

// Focus glow on inputs
document.querySelectorAll('.field input').forEach(input => {
  input.addEventListener('focus', () => {
    input.parentElement.style.transform = 'scale(1.01)';
    input.parentElement.style.transition = 'transform 0.2s ease';
  });
  input.addEventListener('blur', () => {
    input.parentElement.style.transform = 'scale(1)';
  });
});