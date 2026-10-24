
(function(){
  window.SF_HOME_TAB = window.SF_HOME_TAB || (new URLSearchParams(location.search).get('section') === 'descriptive' ? 'descriptive' : 'ibps-clerk');
  window.homeView = function(){
    var tab = window.SF_HOME_TAB || 'ibps-clerk';
    var descriptive = tab === 'descriptive';
    var exam = tab === 'sbi-clerk' ? 'sbi' : 'ibps';
    var title = exam === 'ibps' ? 'IBPS Clerk Mains' : 'SBI Clerk Mains';
    function subjectCard(ex, key, name, detail) {
      return '<article class="section-card"><div class="section-card-top"><span class="badge">'+(ex==='ibps'?'IBPS Clerk Mains':'SBI Clerk Mains')+'</span><span class="small">'+detail+'</span></div><h3>'+name+'</h3><p class="muted">10 sectional tests</p><button class="primary" onclick="showSubjectTests(\\''+ex+'\\',\\''+key+'\\')">View tests →</button></article>';
    }
    var content;
    if(descriptive){
      content = '<div class="section-title"><div><p class="eyebrow">Descriptive practice</p><h2>Choose your PO exam</h2><p class="muted">Your existing descriptive sections and test diversification remain unchanged.</p></div><button class="ghost" onclick="patterns()">View exam pattern →</button></div>'+
      '<div class="grid"><article class="card"><span class="badge">IBPS PO / MT-XVI</span><h2>Essay + Comprehension</h2><p class="muted">Two descriptive sections with 50 practice tests in each.</p><button class="primary" onclick="choose(\'ibps\')">Open IBPS PO →</button></article><article class="card"><span class="badge coral">SBI PO 2026</span><h2>Communication Skills</h2><p class="muted">Email, situation analysis, report, précis and full descriptive practice.</p><button class="primary" onclick="choose(\'sbi\')">Open SBI PO →</button></article></div><div class="notice"><b>Practice integrity:</b> reported questions are labelled as reported; original prompts are labelled as practice.</div>';
    } else {
      content = '<div class="section-title"><div><p class="eyebrow">'+title+'</p><h2>Sectional Tests</h2><p class="muted">Choose a subject to see Test 1 through Test 10.</p></div></div><div class="subject-columns">'+
      (exam==='ibps' ? subjectCard('ibps','reasoning','Reasoning Ability','35 min')+subjectCard('ibps','quant','Quantitative Aptitude','30 min')+subjectCard('ibps','english','English Language','35 min') : subjectCard('sbi','reasoning','Reasoning Ability','45 min · practice adaptation')+subjectCard('sbi','quant','Quantitative Aptitude','45 min')+subjectCard('sbi','english','English Language','35 min'))+
      '</div><div class="notice" style="margin-top:18px"><b>Scoring:</b> objective tests use +1 for a correct answer, zero for unanswered, and a deduction of one-quarter of the marks assigned to that question for a wrong answer. Section details follow published Mains patterns; full-length question banks are still being built. SBI officially combines Reasoning and Computer Aptitude, so Scorefree’s Reasoning-only practice is labelled as an adaptation.</div>';
    }
    document.getElementById('app').innerHTML =
      '<section class="site-intro"><p class="eyebrow">Free bank exam practice</p><h1>SCOREFREE</h1><p class="lead">Practice smarter for bank exams. Take sectional tests, improve descriptive writing, and keep track of your progress.</p></section>'+
      '<div class="home-tabs" role="tablist" aria-label="Choose practice category">'+
      '<button class="home-tab '+(tab==='ibps-clerk'?'active':'')+'" role="tab" aria-selected="'+(tab==='ibps-clerk')+'" onclick="showHomeTab(\'ibps-clerk\')">IBPS Clerk Mains</button>'+
      '<button class="home-tab '+(tab==='sbi-clerk'?'active':'')+'" role="tab" aria-selected="'+(tab==='sbi-clerk')+'" onclick="showHomeTab(\'sbi-clerk\')">SBI Clerk Mains</button>'+
      '<button class="home-tab '+(tab==='descriptive'?'active':'')+'" role="tab" aria-selected="'+descriptive+'" onclick="showHomeTab(\'descriptive\')">Descriptive Test</button></div><section class="home-tab-content">'+content+'</section>'+progressPanel();
    if(new URLSearchParams(location.search).get('section')==='descriptive') history.replaceState({},'',location.pathname);
  };
  window.showHomeTab = function(tab){window.SF_HOME_TAB=tab;S.screen='home';homeView();window.scrollTo(0,0)};
  window.SF_SUBJECT_NAMES = {reasoning:'Reasoning Ability',quant:'Quantitative Aptitude',english:'English Language'};
  window.SF_SECTION_META = {
    ibps:{reasoning:{questions:40,marks:60,minutes:35},quant:{questions:35,marks:50,minutes:30},english:{questions:40,marks:40,minutes:35}},
    sbi:{reasoning:{questions:50,marks:60,minutes:45,note:'Reasoning-only adaptation; official SBI section combines Reasoning & Computer Aptitude'},quant:{questions:50,marks:50,minutes:45},english:{questions:40,marks:40,minutes:35}}
  };
  window.showSubjectTests = function(exam,subject){
    var meta=SF_SECTION_META[exam][subject], name=SF_SUBJECT_NAMES[subject], examName=exam==='ibps'?'IBPS Clerk Mains':'SBI Clerk Mains';
    var cards='';
    for(var i=1;i<=10;i++){
      cards+='<button class="section-test-card" onclick="openClerkPreview(\\''+exam+'\\',\\''+subject+'\\','+i+')"><span class="test-number">Test '+i+'</span><span class="test-metrics">'+meta.questions+' questions · '+meta.marks+' marks</span><span class="test-time">'+meta.minutes+' minutes</span><span class="test-open">Open test preview →</span></button>';
    }
    document.getElementById('app').innerHTML='<button class="ghost" onclick="showHomeTab(\\''+(exam==='ibps'?'ibps-clerk':'sbi-clerk')+'\\')">← Back to subjects</button><section class="test-list-heading"><p class="eyebrow">'+examName+'</p><h2>'+name+' — Sectional Tests</h2><p class="muted">Choose a test below. Each card shows the published section format for reference.</p><div class="test-summary"><span><b>'+meta.questions+'</b> questions</span><span><b>'+meta.marks+'</b> maximum marks</span><span><b>'+meta.minutes+' min</b> time limit</span></div>'+(meta.note?'<p class="small">'+meta.note+'</p>':'')+'</section><div class="section-test-grid">'+cards+'</div><div class="notice" style="margin-top:18px"><b>Important:</b> the links currently open a short interface preview, not a full-length test. The complete question bank and full-length timer are not yet available. Preview results are not official exam predictions.</div>';
    window.scrollTo(0,0);
  };
  window.openClerkPreview = function(exam,subject,test){location.href='./clerk-mains.html?exam='+encodeURIComponent(exam)+'&subject='+encodeURIComponent(subject)+'&test='+(test||1)};
  window.readHistory = function(){try{return JSON.parse(localStorage.getItem('sf-history')||'[]')}catch(e){return []}};
  window.progressPanel = function(){
    var history=readHistory();
    if(!history.length)return '<section class="progress-panel"><div><p class="eyebrow">Your progress</p><h2>Your score history will appear here</h2><p class="muted">Complete a descriptive test and submit it to start saving scores on this device.</p><p class="small">Saved locally in this browser; it will not automatically sync to another device.</p></div></section>';
    var groups={};
    history.forEach(function(r){var k=r.exam+'|'+r.type;if(!groups[k])groups[k]={exam:r.exam,type:r.type,attempts:0,best:0,latest:r};groups[k].attempts++;groups[k].best=Math.max(groups[k].best,Number(r.practiceScore100)||0);if(!groups[k].latest.date||r.date>groups[k].latest.date)groups[k].latest=r});
    var cards=Object.keys(groups).map(function(k){var g=groups[k];return '<div class="progress-item"><b>'+esc(meta[g.exam].title)+' · '+esc(names[g.exam][g.type])+'</b><span>Attempts: '+g.attempts+' · Best: '+g.best+'%</span><span class="small">Latest: Test '+g.latest.test+' · '+g.latest.score+'/'+g.latest.max+' marks</span></div>'}).join('');
    var recent=history.slice(0,12).map(function(r){return '<div class="history-row"><span><b>'+esc(meta[r.exam].title)+' · '+esc(names[r.exam][r.type])+'</b><small>Test '+r.test+' · '+new Date(r.date).toLocaleDateString()+'</small></span><strong>'+r.score+'/'+r.max+' <small>('+r.practiceScore100+'%)</small></strong></div>'}).join('');
    return '<section class="progress-panel"><div class="progress-heading"><div><p class="eyebrow">Saved on this device</p><h2>Your progress</h2></div><button class="secondary" onclick="clearHistory()">Clear history</button></div><div class="progress-grid">'+cards+'</div><div class="history-list"><h3>Recent test scores</h3>'+recent+'</div></section>';
  };
  window.clearHistory = function(){if(confirm('Clear all saved SCOREFREE scores from this browser?')){localStorage.removeItem('sf-history');homeView()}};
  var oldSaveResult=window.saveResult;
  window.saveResult=function(){
    var history=readHistory();
    history.unshift({date:new Date().toISOString(),exam:S.exam,type:S.type,test:S.i+1,score:S.result.marks,max:S.result.max,practiceScore100:S.result.total});
    try{localStorage.setItem('sf-history',JSON.stringify(history.slice(0,200)))}catch(e){console.warn('Score history could not be saved in this browser',e)}
  };
  homeView();
})();
