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
      <p class="eyebrow">Free Clerk Mains Quant and Reasoning practice</p>
      <h2>IBPS &amp; SBI Clerk Mains Quant and Reasoning</h2>
      <p class="muted">SCOREFREE is a free practice platform focused on IBPS Clerk Mains and SBI Clerk Mains Quantitative Aptitude and Reasoning Ability. Practise challenging timed sectional tests, mixed-topic questions and detailed solutions.</p>
      <p class="muted">Build speed, accuracy and problem-solving ability with exam-style Quant and Reasoning practice for both Clerk Mains exams.</p>
    `;
    app.appendChild(section);
  }

  const observer=new MutationObserver(addSeoIntro);
  document.addEventListener('DOMContentLoaded',function(){
    const app=document.getElementById('app');
    if(app){observer.observe(app,{childList:true,subtree:true});addSeoIntro();}
  });
})();
