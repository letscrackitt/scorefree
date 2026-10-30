(function(){
  if(!window.SF_BANK) return;
  function makeQ(topic,q,answer,exp,ctx){
    answer=Math.round(answer);
    var ds=[5,10,15,20,25,30,40,50,60,75,100], vals=[answer];
    ds.forEach(function(d){if(vals.length<5&&!vals.includes(answer+d)) vals.push(answer+d); if(vals.length<5&&answer-d>0&&!vals.includes(answer-d)) vals.push(answer-d);});
    var opts=vals.slice(0,5).map(String);
    var seed=q.length; for(var i=opts.length-1;i>0;i--){seed=(seed*9301+49297)%233280;var j=seed%(i+1);var t=opts[i];opts[i]=opts[j];opts[j]=t;}
    var item={topic:topic,q:q,opts:opts,ans:opts.indexOf(String(answer)),exp:exp};
    if(ctx){item.setTitle=ctx.title;item.setIntro=ctx.intro;} return item;
  }
  function buildTest(test,target){
    var out=[], k=test, A=180+k*17, B=220+k*13, C=260+k*11, D=300+k*19, E=340+k*7;
    var ctx={title:'Data Interpretation · Quarterly advances · Set '+test,intro:'The table shows the advances (₹ lakh) made by five bank branches during Q1. Branch A: '+A+'; B: '+B+'; C: '+C+'; D: '+D+'; E: '+E+'. In Q2, advances of A, C and E increased by 20%, 15% and 10% respectively, while B and D decreased by 10% and 5%. Use these figures for Questions 1–5.'};
    var q2={A:A*1.2,B:B*.9,C:C*1.15,D:D*.95,E:E*1.1};
    out.push(makeQ('Data Interpretation · Table','Approximately what were the combined Q2 advances of branches A and C?',q2.A+q2.C,'Q2 A = '+A+' × 1.20 = '+q2.A.toFixed(1)+'; Q2 C = '+C+' × 1.15 = '+q2.C.toFixed(1)+'. Combined = ₹'+(q2.A+q2.C).toFixed(1)+' lakh.',ctx));
    out.push(makeQ('Data Interpretation · Table','Approximately by what percentage were the Q2 advances of branch E higher than those of branch B?',(q2.E-q2.B)*100/q2.B,'Q2 E = '+E+' × 1.10 = '+q2.E.toFixed(1)+'; Q2 B = '+B+' × 0.90 = '+q2.B.toFixed(1)+'. Percentage excess = ('+q2.E.toFixed(1)+' − '+q2.B.toFixed(1)+') / '+q2.B.toFixed(1)+' × 100 = '+((q2.E-q2.B)*100/q2.B).toFixed(2)+'%.',ctx));
    var gcd=function(a,b){return b?gcd(b,a%b):a;}; var ratioDiv=gcd(C,D), ratioFirst=C/ratioDiv;
    out.push(makeQ('Data Interpretation · Table','When the Q1 advances of branches C and D are expressed in their simplest ratio, what is the first term?',ratioFirst,'C:D = '+C+':'+D+'. Dividing both terms by HCF '+ratioDiv+' gives '+(C/ratioDiv)+':'+(D/ratioDiv)+'. The first term is '+ratioFirst+'.',ctx));
    out.push(makeQ('Data Interpretation · Table','Approximately how much remains outstanding if 40% of Q2 advances of branch D are recovered?',q2.D*.6,'Outstanding = 60% of '+q2.D.toFixed(1)+' = ₹'+(q2.D*.6).toFixed(1)+' lakh.',ctx));
    out.push(makeQ('Data Interpretation · Table','Approximately what is the average Q1 advance of branches A, B, C and E?',(A+B+C+E)/4,'Average = ('+[A,B,C,E].join(' + ')+') / 4 = ₹'+((A+B+C+E)/4).toFixed(2)+' lakh.',ctx));
    var n=k;
    var cp=800+50*n, profit=15+(n%4)*5, discount=10+(n%3)*5, sp=cp*(100+profit)/100, mp=sp*100/(100-discount);
    out.push(makeQ('Profit, Loss and Discount','An article costing ₹'+cp+' is sold at a profit of '+profit+'% after allowing a discount of '+discount+'% on its marked price. Find the marked price.',mp,'Selling price = '+cp+' × '+(100+profit)+'/100 = ₹'+sp.toFixed(2)+'. Marked price = '+sp.toFixed(2)+' × 100/'+(100-discount)+' = ₹'+mp.toFixed(2)+'.'));
    var P=5000+500*n, rate=8+(n%3), years=2+(n%2), ci=P*Math.pow(1+rate/100,years)-P;
    out.push(makeQ('Compound Interest','Find the compound interest on ₹'+P+' at '+rate+'% p.a., compounded annually, for '+years+' years.',ci,'Amount = '+P+' × (1 + '+rate+'/100)^'+years+' = ₹'+(P+ci).toFixed(2)+'. Compound interest = ₹'+ci.toFixed(2)+'.'));
    var x=12+(n%5)*2, y=15+(n%4)*3, together=x*y/(x+y), days=3+(n%3), rem=1-days/together, solo=rem*y;
    out.push(makeQ('Time and Work','A and B can complete a job in '+x+' and '+y+' days respectively. They work together for '+days+' days, after which A leaves. How many additional days will B require to finish the remaining work?',solo,'One-day joint work = 1/'+x+' + 1/'+y+' = '+(1/x+1/y).toFixed(4)+'. Remaining work after '+days+' days = '+rem.toFixed(4)+'. B alone takes '+rem.toFixed(4)+' × '+y+' = '+solo.toFixed(2)+' days.'));
    var train=150+10*n, platform=180+10*(n%4), sec=18+(n%4)*3, speed=(train+platform)*18/(5*sec);
    out.push(makeQ('Trains','A train '+train+' m long crosses a '+platform+' m platform in '+sec+' seconds. Find its speed in km/h.',speed,'Distance covered = '+train+' + '+platform+' = '+(train+platform)+' m. Speed = '+(train+platform)+'/'+sec+' × 18/5 = '+speed.toFixed(2)+' km/h.'));
    var still=18+n%5*2, stream=3+n%3, dist=60+10*n, down=still+stream, up=still-stream, avg=2*dist/(dist/down+dist/up);
    out.push(makeQ('Boats and Streams','A boat travels '+dist+' km downstream and the same distance upstream. Its speed in still water is '+still+' km/h and the stream speed is '+stream+' km/h. Find its average speed for the round trip.',avg,'Downstream speed = '+down+' km/h; upstream speed = '+up+' km/h. Total time = '+dist+'/'+down+' + '+dist+'/'+up+' hours. Average speed = '+(2*dist)+' / total time = '+avg.toFixed(2)+' km/h.'));
    var m=20+n%6*5, ratio=2+n%3, qty= m*(ratio+1), milk=qty*ratio/(ratio+1);
    out.push(makeQ('Mixture and Alligation','A '+qty+' litre mixture contains milk and water in the ratio '+ratio+':1. How many litres of milk must be added to make the ratio 3:1?',3*qty/4-milk,'Initial milk = '+qty+' × '+ratio+'/'+(ratio+1)+' = '+milk+' L. For a 3:1 ratio, milk must be 3/4 × '+qty+' = '+(3*qty/4)+' L. Milk to add = '+(3*qty/4-milk)+' L.'));
    var a=24+n%4*3,b=18+n%5*2,c=12+n%3*3, rateSum=1/a+1/b+1/c, twork=1/rateSum;
    out.push(makeQ('Time and Work','A, B and C can complete a work individually in '+a+', '+b+' and '+c+' days. In how many days can they complete it working together?',twork,'Combined rate = 1/'+a+' + 1/'+b+' + 1/'+c+' = '+rateSum.toFixed(5)+' of the work per day. Time = 1/'+rateSum.toFixed(5)+' = '+twork.toFixed(2)+' days.'));
    var n1=30+n*2,n2=25+n,overall=68+n%5,avgA=overall+4,avgB=((n1+n2)*overall-n1*avgA)/n2;
    out.push(makeQ('Averages','The average score of '+n1+' candidates in group A and '+n2+' candidates in group B is '+overall+'. If group A averages '+avgA+', find the average score of group B.',avgB,'Combined total = ('+n1+' + '+n2+') × '+overall+' = '+((n1+n2)*overall)+'. Group A total = '+n1+' × '+avgA+' = '+(n1*avgA)+'. Group B average = ('+((n1+n2)*overall)+' − '+(n1*avgA)+')/'+n2+' = '+avgB.toFixed(2)+'.'));
    var principal=6000+n*500, siRate=7+n%4, months=18+n%4*6, si=principal*siRate*months/1200;
    out.push(makeQ('Simple Interest','A sum of ₹'+principal+' is invested at '+siRate+'% simple interest per annum for '+months+' months. Find the interest earned.',si,'SI = P × R × T / 100 = '+principal+' × '+siRate+' × ('+months+'/12) / 100 = ₹'+si.toFixed(2)+'.'));
    var incomeA=24000+n*500, incomeB=incomeA*(5+n%3)/(4+n%3), expenseA=incomeA*(70+n%5)/100, expenseB=incomeB*(65+n%6)/100, saveDiff=(incomeA-expenseA)-(incomeB-expenseB);
    out.push(makeQ('Partnership and Income','P earns ₹'+incomeA+' per month and saves '+(100-(70+n%5))+'% of it. Q earns ₹'+incomeB.toFixed(0)+' and saves '+(100-(65+n%6))+'% of it. Find the difference between their monthly savings.',Math.abs(saveDiff),'P saves '+(100-(70+n%5))+'% of '+incomeA+' = ₹'+(incomeA-expenseA).toFixed(2)+'. Q saves '+(100-(65+n%6))+'% of ₹'+incomeB.toFixed(0)+' = ₹'+(incomeB-expenseB).toFixed(2)+'. Difference = ₹'+Math.abs(saveDiff).toFixed(2)+'.'));
    var r=7+n%5, h=10+n%4, volume=Math.PI*r*r*h;
    out.push(makeQ('Mensuration','A cylindrical tank has radius '+r+' m and height '+h+' m. Find its capacity in cubic metres (use π = 22/7).',22/7*r*r*h,'Volume = πr²h = 22/7 × '+r+'² × '+h+' = '+(22/7*r*r*h).toFixed(2)+' m³.'));
    var basev=1000+100*n, inc=10+n%4*5, dec=5+n%3*5, finalv=basev*(1+inc/100)*(1-dec/100);
    out.push(makeQ('Successive Percentage Change','A value of '+basev+' is increased by '+inc+'% and then decreased by '+dec+'%. Find the final value.',finalv,'Final value = '+basev+' × '+(100+inc)+'/100 × '+(100-dec)+'/100 = '+finalv.toFixed(2)+'.'));
    var dist2=180+20*n, s1=40+n%5*5, s2=s1+10+n%3*5, timeDiff=dist2/s1-dist2/s2;
    out.push(makeQ('Speed, Time and Distance','A car covers a fixed distance at '+s1+' km/h. If its speed were '+s2+' km/h, it would take '+timeDiff.toFixed(2)+' hours less. Find the distance.',dist2,'Let distance be D. D/'+s1+' − D/'+s2+' = '+timeDiff.toFixed(2)+'. Solving gives D = '+dist2+' km.'));
    var p2=10000+1000*n, r2=10+n%4, ciMinusSi=p2*Math.pow(r2/100,2);
    out.push(makeQ('Simple and Compound Interest','Find the difference between compound interest and simple interest on ₹'+p2+' for 2 years at '+r2+'% per annum.',ciMinusSi,'For 2 years, CI − SI = P × (R/100)² = '+p2+' × ('+r2+'/100)² = ₹'+ciMinusSi.toFixed(2)+'.'));
    var cheap=30+n%5*5, dear=60+n%4*5, target=cheap+((dear-cheap)*(2+(n%3)))/5, mixqty=50+5*n, cheapqty=mixqty*(dear-target)/(dear-cheap);
    out.push(makeQ('Alligation','Tea worth ₹'+cheap+' per kg is mixed with tea worth ₹'+dear+' per kg to obtain a mixture worth ₹'+target.toFixed(2)+' per kg. How many kg of the cheaper tea are required to prepare '+mixqty+' kg of the mixture?',cheapqty,'By alligation, cheaper:dearer quantity = ('+dear+' − '+target.toFixed(2)+'):('+target.toFixed(2)+' − '+cheap+') = '+(dear-target).toFixed(2)+':'+(target-cheap).toFixed(2)+'. Cheaper tea required = '+mixqty+' × '+(dear-target).toFixed(2)+'/'+(dear-cheap)+' = '+cheapqty.toFixed(2)+' kg.'));

    for(var j=1;out.length<target;j++){
      var z=test*37+j, typ=j%9, p, r, ans, q, ex;
      if(typ===1){p=400+z*10;r=10+(z%5)*5;ans=p*r/100;q='A sum of ₹'+p+' is invested at '+r+'% simple interest for one year. Find the interest.';ex='SI = P×R×T/100 = '+p+'×'+r+'/100 = ₹'+ans+'.';}
      else if(typ===2){p=600+z*20;r=20+(z%4)*5;ans=p*(100+r)/100;q='An article costs ₹'+p+' and is sold at a profit of '+r+'%. Find its selling price.';ex='SP = CP×(100+profit)/100 = '+p+'×'+(100+r)+'/100 = ₹'+ans+'.';}
      else if(typ===3){p=500+z*10;r=2+(z%6);ans=p*r;q='Two quantities are in the ratio '+r+':1 and their sum is '+(p*(r+1))+'. Find the larger quantity.';ex='Larger quantity = '+(p*(r+1))+'×'+r+'/'+(r+1)+' = '+ans+'.';}
      else if(typ===4){p=20+(z%20);r=5+(z%5)*5;ans=p*(100+r)/100;q='A number is '+p+'. It is increased by '+r+'%. Find the new number.';ex='New value = '+p+'×'+(100+r)+'/100 = '+ans+'.';}
      else if(typ===5){p=12+(z%8);r=15+(z%5)*5;ans=p*r;q='A vehicle travels at '+r+' km/h for '+p+' hours. Find the distance covered.';ex='Distance = speed×time = '+r+'×'+p+' = '+ans+' km.';}
      else if(typ===6){p=200+z*10;r=10+(z%5)*5;ans=p*(100-r)/100;q='An item marked at ₹'+p+' is sold at a discount of '+r+'%. Find its selling price.';ex='SP = MP×'+(100-r)+'/100 = '+p+'×'+(100-r)+'/100 = ₹'+ans+'.';}
      else if(typ===7){p=30+(z%15);r=20+(z%10);ans=p+r;q='The average of two numbers is '+p+'. One number is '+(p-r)+'. Find the other number.';ex='Sum = 2×'+p+' = '+(2*p)+'. Other number = '+(2*p)+' − '+(p-r)+' = '+ans+'.';}
      else if(typ===8){p=100+z*5;r=2+(z%5);ans=p*r;q='If '+r+' identical machines produce '+ans+' units in one day, how many units does each machine produce?';ex='Output per machine = '+ans+'/'+r+' = '+p+'.';}
      else{p=12+(z%10);r=15+(z%6);ans=p*r;q='A person completes '+p+' units of work per day for '+r+' days. Find the total work completed.';ex='Total work = '+p+'×'+r+' = '+ans+' units.';}
      out.push(makeQ('Quantitative Aptitude · Arithmetic',q,ans,ex));
    }
    return out;
  }
  for(var test=1;test<=10;test++){
    SF_BANK.ibps.quant[test]=buildTest(test,35);
    SF_BANK.sbi.quant[test]=buildTest(test,50);
  }
})();