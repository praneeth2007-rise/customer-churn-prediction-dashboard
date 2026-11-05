(() => {
 const d=window.COMPARISON_DATA||{},ink='#171717',muted='#726E67',border='#E5E1D9';
 const base={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'DM Sans, sans-serif',size:10,color:muted},margin:{l:46,r:16,t:10,b:70},xaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9},tickangle:-12},yaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9},rangemode:'tozero',range:[0,100],ticksuffix:'%',title:{text:'Percent (%)',font:{size:9}}},legend:{orientation:'h',y:-.3,font:{size:9}},hoverlabel:{bgcolor:'#fff',bordercolor:border,font:{color:ink,size:10}}};
 const cfg={responsive:true,displayModeBar:false};
 const render=(id,traces,layout={})=>{const el=document.getElementById(id);if(!el)return;if(window.Plotly)Plotly.newPlot(el,traces,{...base,...layout},cfg);else el.textContent='Interactive chart unavailable. Check your connection and reload.'};
 const colors=d.keys.map(k=>d.colors[k]);
 const metric=(id,key,label)=>render(id,[{type:'bar',x:d.labels,y:d[key],marker:{color:colors},text:d[key].map(v=>v.toFixed(2)+'%'),textposition:'outside',cliponaxis:false,hovertemplate:'%{x}<br>'+label+': %{y:.4f}%<extra></extra>'}],{margin:{...base.margin,t:28},yaxis:{...base.yaxis,range:[0,Math.min(110,Math.ceil(Math.max(...d[key])/10)*10+10)]}});
 metric('accuracy-chart','accuracy','Accuracy');metric('precision-chart','precision','Churn precision');metric('recall-chart','recall','Churn recall');metric('f1-chart','f1','Churn F1-score');
 const names=[['Accuracy','accuracy'],['Churn precision','precision'],['Churn recall','recall'],['Churn F1-score','f1']];
 const traces=d.keys.map((key,i)=>({type:'bar',name:d.labels[i],x:names.map(x=>x[0]),y:names.map(x=>d[x[1]][i]),marker:{color:d.colors[key]},hovertemplate:'%{x}<br>'+d.labels[i]+': %{y:.4f}%<extra></extra>'}));
 render('all-metrics-chart',traces,{barmode:'group',margin:{...base.margin,b:55},xaxis:{...base.xaxis,tickangle:0},yaxis:{...base.yaxis,range:[0,110]}});
 const side=document.querySelector('.sidebar'),scrim=document.querySelector('.mobile-scrim'),toggle=document.querySelector('.sidebar-toggle');
 const close=()=>{side?.classList.remove('open');scrim?.classList.remove('open');toggle?.setAttribute('aria-expanded','false')};
 toggle?.addEventListener('click',()=>{const open=!side.classList.contains('open');side.classList.toggle('open',open);scrim?.classList.toggle('open',open);toggle.setAttribute('aria-expanded',String(open))});scrim?.addEventListener('click',close);side?.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',close));
})();
