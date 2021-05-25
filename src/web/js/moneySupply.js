const width = window.innerWidth;
const height = window.innerHeight;
const margin = {top: 20, right: 100, bottom: 30, left: 100};

// http://data.eastmoney.com/cjsj/hbgyl.html
// 月份 M2数量 M2同比增长 M2环比增长 M1数量 M1同比增长 M1环比增长 M0数量 M0同比增长 M0环比增长 
d3.json('../../data/moneySupply.json').then((data) => {
    const reverseData = data.reverse();
    const dateArr = [];
    const serieArr = [[], [], []];
    for (let item of reverseData) {
        const arr = item.split(',');
        dateArr.push(new Date(arr[0]));
        serieArr[0].push(Number(arr[7]));
        serieArr[1].push(Number(arr[4]));
        serieArr[2].push(Number(arr[1]));
    }

    const x = d3.scaleUtc()
        .domain(d3.extent(dateArr))
        .range([margin.left, width - margin.right]);

    const y = d3.scaleLinear()
        .domain([
            d3.min(serieArr, d => d3.min(d)),
            d3.max(serieArr, d => d3.max(d))
        ])
        .nice()
        .range([height - margin.bottom, margin.top]);

    const keys = ['m0', 'm1', 'm2'];
    const z = d3.scaleOrdinal(d3.schemeCategory10).domain(keys);

    const line = d3.line()
        .defined(d => !isNaN(d))
        .x((d, i) => x(dateArr[i]))
        .y(d => y(d));

    const yAxis = g => g
        .attr("transform", `translate(${margin.left},0)`)
        .call(d3.axisLeft(y))
        // .call(g => g.select(".domain").remove())
        .call(g => g.select(".tick:last-of-type text").clone()
            .attr("x", 3)
            .attr("text-anchor", "start")
            .attr("font-weight", "bold")
            .text('亿'));

    const xAxis = g => g
        .attr("transform", `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x).ticks(width / 80).tickSizeOuter(0));

    const chart = () => {
        const svg = d3.create('svg')
            .attr("viewBox", [0, 0, width, height])
            .style("-webkit-tap-highlight-color", "transparent")
            .style("overflow", "visible");

        svg.append("g")
            .call(xAxis);

        svg.append("g")
            .call(yAxis);

        const colors = ['red', 'green', 'blue'];

        const serie = svg.append('g')
            .selectAll('g')
            .data(serieArr)
            .join('g');

        serie.append('path')
            .attr("fill", "none")
            .attr("stroke-width", 1.5)
            .attr("stroke-linejoin", "round")
            .attr("stroke-linecap", "round")
            .attr('stroke', (d, i) => z(keys[i]))
            .attr('d', d => line(d));

        serie.append("text")
            .datum((d, i) => ({ key: keys[i], value: d[d.length - 1] }))
            .attr("x", x.range()[1] + 3)
            .attr("y", d => y(d.value))
            .attr("dy", "0.35em")
            .attr("fill", d => z(d.key))
            .attr("stroke", null)
            .text(d => d.key)

        return svg.node();
    }

    document.body.appendChild(chart());
});