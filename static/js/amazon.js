(() => {
 const c=window.AMAZON_CHARTS||{},teal='#0D9488',blue='#2563EB',ink='#171717',muted='#726E67',border='#E5E1D9';
 const base={paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{family:'DM Sans, sans-serif',size:10,color:muted},margin:{l:42,r:18,t:8,b:38},xaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9}},yaxis:{gridcolor:border,zerolinecolor:border,linecolor:border,tickfont:{size:9}},hoverlabel:{bgcolor:'#fff',bordercolor:border,font:{color:ink,size:10}}};
 const cfg={responsive:true,displayModeBar:false};
 const draw=(id,traces,layout={})=>{const el=document.getElementById(id);if(!el)return;if(window.Plotly)Plotly.newPlot(el,traces,{...base,...layout},cfg);else el.textContent='Interactive chart unavailable. Check your connection and reload.';};
 const bar=(id,d,color=teal,layout={})=>draw(id,[{type:'bar',x:d.labels,y:d.values,marker:{color},hovertemplate:'%{x}<br>%{y:,} users<extra></extra>'}],{yaxis:{...base.yaxis,rangemode:'tozero',title:{text:'Users',font:{size:9}}},...layout});
 draw('plan-chart',[{type:'pie',hole:.58,labels:c.plans.labels,values:c.plans.values,marker:{colors:[teal,blue,'#a8aaa6'],line:{color:'#fff',width:3}},textinfo:'label+value',textposition:'outside',hovertemplate:'%{label}: %{value:,}<extra></extra>'}],{margin:{l:12,r:12,t:12,b:12},showlegend:false,uniformtext:{minsize:8,mode:'hide'}});
 bar('payment-chart',c.payments,blue,{margin:{l:42,r:12,t:5,b:54},xaxis:{...base.xaxis,tickangle:-12}});
 bar('duration-chart',c.duration,teal,{yaxis:{...base.yaxis,rangemode:'tozero',title:{text:'Records',font:{size:9}}}});
 bar('device-chart',c.devices,blue);bar('renewal-chart',c.renewal,teal);bar('usage-chart',c.usage,blue);
 bar('support-chart',c.support,teal,{xaxis:{...base.xaxis,title:{text:'Recorded interactions',font:{size:9}}}});
 const side=document.querySelector('.sidebar'),scrim=document.querySelector('.mobile-scrim'),toggle=document.querySelector('.sidebar-toggle');
 const close=()=>{side?.classList.remove('open');scrim?.classList.remove('open');toggle?.setAttribute('aria-expanded','false')};
 toggle?.addEventListener('click',()=>{const open=!side.classList.contains('open');side.classList.toggle('open',open);scrim?.classList.toggle('open',open);toggle.setAttribute('aria-expanded',String(open))});scrim?.addEventListener('click',close);side?.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',close));
})();
