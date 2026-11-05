(() => {
  const charts = window.JIO_CHARTS || {};
  const ink = '#171717', muted = '#726E67', border = '#E5E1D9', blue = '#2563EB';
  const base = {
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'DM Sans, sans-serif', size: 10, color: muted},
    margin: {l: 42, r: 18, t: 8, b: 38},
    xaxis: {gridcolor: border, zerolinecolor: border, linecolor: border, tickfont: {size: 9}},
    yaxis: {gridcolor: border, zerolinecolor: border, linecolor: border, tickfont: {size: 9}},
    legend: {orientation: 'h', y: -0.2, font: {size: 9}},
    hoverlabel: {bgcolor: '#fff', bordercolor: border, font: {color: ink, size: 10}}
  };
  const config = {responsive: true, displayModeBar: false};
  const draw = (id, data, layout) => {
    const el = document.getElementById(id);
    if (el && window.Plotly) Plotly.newPlot(el, data, {...base, ...layout}, config);
    else if (el) el.textContent = 'Interactive chart unavailable. Check your connection and reload.';
  };

  draw('status-chart', [{type: 'pie', hole: .62, labels: charts.status.labels, values: charts.status.values,
    marker: {colors: ['#2563EB', '#a8a49b', '#d8d3c9'], line: {color: '#fff', width: 3}},
    textinfo: 'label+value', textposition: 'outside', hovertemplate: '%{label}: %{value:,}<extra></extra>'}],
    {margin: {l: 12, r: 12, t: 12, b: 12}, showlegend: false, uniformtext: {minsize: 8, mode: 'hide'}});
  draw('contract-chart', [
    {type: 'bar', name: 'Stayed', x: charts.contract.labels, y: charts.contract.stayed, marker: {color: '#c9c5bc'}, hovertemplate: '%{x}<br>Stayed: %{y:,}<extra></extra>'},
    {type: 'bar', name: 'Churned', x: charts.contract.labels, y: charts.contract.churned, marker: {color: blue}, hovertemplate: '%{x}<br>Churned: %{y:,}<extra></extra>'}
  ], {barmode: 'group', yaxis: {...base.yaxis, title: {text: 'Customers', font: {size: 9}}}});
  draw('tenure-chart', [{type: 'bar', x: charts.tenure.labels, y: charts.tenure.rates, marker: {color: blue},
    customdata: charts.tenure.counts, hovertemplate: '%{x} months<br>Churn rate: %{y:.2f}%<br>Stayed/Churned base: %{customdata:,}<extra></extra>'}],
    {yaxis: {...base.yaxis, rangemode: 'tozero', title: {text: 'Churn rate (%)', font: {size: 9}}, ticksuffix: '%'}});
  draw('state-chart', [{type: 'bar', orientation: 'h', x: charts.states.values, y: charts.states.labels,
    marker: {color: blue}, hovertemplate: '%{y}: %{x:,} customers<extra></extra>'}],
    {margin: {l: 112, r: 12, t: 5, b: 28}, xaxis: {...base.xaxis, title: {text: 'Customers', font: {size: 9}}}, yaxis: {...base.yaxis, gridcolor: 'rgba(0,0,0,0)', autorange: 'reversed'}});
  draw('service-chart', [{type: 'bar', orientation: 'h', x: charts.services.rates, y: charts.services.labels,
    marker: {color: '#2563EB'}, hovertemplate: '%{y}: %{x:.1f}% marked Yes<extra></extra>'}],
    {margin: {l: 145, r: 16, t: 5, b: 32}, xaxis: {...base.xaxis, range: [0, 100], ticksuffix: '%', title: {text: 'Share of non-missing responses', font: {size: 9}}}, yaxis: {...base.yaxis, gridcolor: 'rgba(0,0,0,0)', autorange: 'reversed'}});
  draw('revenue-chart', [{type: 'bar', x: charts.revenue.labels, y: charts.revenue.values, marker: {color: ['#a8a49b', blue, '#d8d3c9']},
    hovertemplate: '%{x}<br>Average total revenue: %{y:,.2f}<extra></extra>'}],
    {yaxis: {...base.yaxis, rangemode: 'tozero', title: {text: 'Average total revenue', font: {size: 9}}}});

  const sidebar = document.querySelector('.sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  const toggle = document.querySelector('.sidebar-toggle');
  const close = () => { sidebar?.classList.remove('open'); scrim?.classList.remove('open'); toggle?.setAttribute('aria-expanded', 'false'); };
  toggle?.addEventListener('click', () => {
    const open = !sidebar.classList.contains('open');
    sidebar.classList.toggle('open', open); scrim?.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  });
  scrim?.addEventListener('click', close);
  sidebar?.querySelectorAll('a[href^="#"]').forEach((link) => link.addEventListener('click', close));
})();
