(() => {
 const c=window.NETFLIX_CHARTS||{},red='#E50914',ink='#171717',muted='#726E67',border='#E5E1D9';
 const base={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'DM Sans, sans-serif',size:10,color:muted},margin:{l:42,r:18,t:8,b:38},xaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9}},yaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9}},legend:{orientation:'h',y:-.2,font:{size:9}},hoverlabel:{bgcolor:'#fff',bordercolor:border,font:{color:ink,size:10}}};
 const cfg={responsive:true,displayModeBar:false};
 const draw=(id,traces,layout={})=>{const el=document.getElementById(id);if(!el)return;if(window.Plotly)Plotly.newPlot(el,traces,{...base,...layout},cfg);else el.textContent='Interactive chart unavailable. Check your connection and reload.';};
 const grouped=(id,d,extra={})=>draw(id,[{type:'bar',name:'Stayed',x:d.labels,y:d.stayed,marker:{color:'#c9c5bc'},hovertemplate:'%{x}<br>Stayed: %{y:,}<extra></extra>'},{type:'bar',name:'Churned',x:d.labels,y:d.churned,marker:{color:red},hovertemplate:'%{x}<br>Churned: %{y:,}<extra></extra>'}],{barmode:'group',...extra});
 draw('status-chart',[{type:'pie',hole:.62,labels:c.status.labels,values:c.status.values,marker:{colors:[red,'#aaa69e'],line:{color:'#fff',width:3}},textinfo:'label+value',textposition:'outside',hovertemplate:'%{label}: %{value:,}<extra></extra>'}],{margin:{l:12,r:12,t:12,b:12},showlegend:false,uniformtext:{minsize:8,mode:'hide'}});
 grouped('subscription-chart',c.subscription,{yaxis:{...base.yaxis,title:{text:'Customers',font:{size:9}}}});
 grouped('region-chart',c.region,{margin:{l:72,r:12,t:5,b:55},xaxis:{...base.xaxis,tickangle:-20},yaxis:{...base.yaxis,title:{text:'Customers',font:{size:9}}}});
 grouped('device-chart',c.device,{yaxis:{...base.yaxis,title:{text:'Customers',font:{size:9}}}});
 draw('age-chart',[{type:'bar',x:c.age.labels,y:c.age.rates,customdata:c.age.counts,marker:{color:red},hovertemplate:'Age %{x}<br>Churn rate %{y:.2f}%<br>Records %{customdata:,}<extra></extra>'}],{yaxis:{...base.yaxis,rangemode:'tozero',ticksuffix:'%',title:{text:'Churn rate',font:{size:9}}}});
 const meanChart=(id,d,axis)=>draw(id,[{type:'bar',x:d.labels,y:d.values,marker:{color:[red,'#aaa69e']},hovertemplate:'%{x}<br>Mean: %{y:.2f}<extra></extra>'}],{yaxis:{...base.yaxis,rangemode:'tozero',title:{text:axis,font:{size:9}}}});
 meanChart('watch-chart',c.watch,'Average watch hours');meanChart('fee-chart',c.fee,'Average monthly fee');
 const side=document.querySelector('.sidebar'),scrim=document.querySelector('.mobile-scrim'),toggle=document.querySelector('.sidebar-toggle');
 const close=()=>{side?.classList.remove('open');scrim?.classList.remove('open');toggle?.setAttribute('aria-expanded','false')};
 toggle?.addEventListener('click',()=>{const open=!side.classList.contains('open');side.classList.toggle('open',open);scrim?.classList.toggle('open',open);toggle.setAttribute('aria-expanded',String(open))});scrim?.addEventListener('click',close);side?.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',close));
})();
