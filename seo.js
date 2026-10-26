(function(){
  function addSeoIntro(){
    const app=document.getElementById('app');
    if(!app)return;
    if(document.getElementById('seo-intro'))return;
    const hero=app.querySelector('.hero');
    if(!hero)return;

    const section=document.createElement('section');
    section.id='seo-intro';
    section.className='card';
    section.style.cssText='max-width:960px;margin:40px auto 10px';
    section.innerHTML=`
      <p class="eyebrow">Free bank exam descriptive practice</p>
      <h2>IBPS Clerk, SBI Clerk &amp; PO Practice</h2>
      <p class="muted">SCOREFREE is a free practice platform for bank exam aspirants: IBPS Clerk Mains and SBI Clerk Mains sectional tests, plus IBPS PO essay and comprehension and SBI PO email, situation analysis, report and précis writing.</p>
      <p class="muted">Use SCOREFREE to build exam-ready writing habits with practice tests, word-count guidance, transparent practice scoring and learning pointers.</p>
    `;
    app.appendChild(section);
  }

  const observer=new MutationObserver(addSeoIntro);
  document.addEventListener('DOMContentLoaded',function(){
    const app=document.getElementById('app');
    if(app){observer.observe(app,{childList:true,subtree:true});addSeoIntro();}
  });
})();
