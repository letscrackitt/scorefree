// Pre-test confirmation: selecting a test should not consume time immediately.
(function(){
  window.start=function(i){
    stop();
    S.i=i;
    S.answer='';
    S.result=null;
    S.sec=900;
    S.paused=false;
    S.screen='test';
    render();
    showStartNotice();
  };

  window.beginTest=function(){
    const modal=document.getElementById('start-notice');
    if(modal)modal.remove();
    S.sec=900;
    S.paused=false;
    clock();
    trackEvent('test_started',{exam:S.exam,section:S.type,test_number:S.i+1});
    const a=document.getElementById('answer');
    if(a){a.focus();a.setSelectionRange(a.value.length,a.value.length)}
  };

  window.cancelTest=function(){
    const modal=document.getElementById('start-notice');
    if(modal)modal.remove();
    stop();
    trackEvent('test_start_cancelled',{exam:S.exam,section:S.type,test_number:S.i+1});
    S.screen='tests';
    render();
  };

  function showStartNotice(){
    const old=document.getElementById('start-notice');
    if(old)old.remove();
    const modal=document.createElement('div');
    modal.id='start-notice';
    modal.style.cssText='position:fixed;inset:0;background:rgba(20,18,30,.52);display:flex;align-items:center;justify-content:center;padding:20px;z-index:9999;backdrop-filter:blur(5px)';
    modal.innerHTML='<div style="width:min(440px,100%);background:#fff;border-radius:22px;padding:30px;box-shadow:0 24px 70px rgba(0,0,0,.25);text-align:center"><div style="font-size:2.2rem;margin-bottom:8px">⏱️</div><p class="eyebrow" style="margin-bottom:8px">Ready when you are</p><h2 style="margin:0 0 10px">Test '+String(S.i+1).padStart(2,'0')+' is about to begin</h2><p class="muted" style="margin:0 auto 22px;line-height:1.65">You will have <b>15 minutes</b> to complete this test. The timer starts only when you click <b>Start test</b>.</p><div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap"><button class="secondary" onclick="cancelTest()">Not yet</button><button class="primary" onclick="beginTest()">Start test →</button></div></div>';
    document.body.appendChild(modal);
  }
})();
