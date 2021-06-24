class LineGraph {

    constructor({
        width = 300,
        height = 150,
        container,
        margin = { top: 0, right: 0, bottom: 0, left: 0 }
    }) {
        this.width = width;
        this.height = height;
        this.margin = margin;
        this.svgSelection = d3.create('svg').attr('viewBox', [0, 0, width, height]);
        this.xAxisSelection = this.svgSelection.append('g');
        this.yAxisSelection = this.svgSelection.append('g');
        this.seriesWrapperSelection = this.svgSelection.append('g');

        if (container) {
            if (container instanceof HTMLElement) {
                container.appendChild(this.svgSelection.node());
            } else {
                document.querySelector(container).appendChild(this.svgSelection.node());
            }
        }
    }

    setData(data) {
        const width = this.width;
        const height = this.height;
        const margin = this.margin;
        const { labels, series } = data;

        this.data = data;

        this.xScale = d3.scaleUtc()
            .domain(d3.extent(labels))
            .range([margin.left, width - margin.left]);
        
        this.yScale = d3.scaleLinear()
            .domain([
                d3.min(series, d => d3.min(d.data)),
                d3.max(series, d => d3.max(d.data))
            ])
            .nice()
            .range([height - margin.bottom, margin.top]);

        this.line = d3.line()
            .defined(d => !isNaN(d) && d !== null)
            .x((d, i) => this.xScale(labels[i]))
            .y(d => this.yScale(d));
    }

    render() {
        const width = this.width;
        const height = this.height;
        const margin = this.margin;
        const xScale = this.xScale;
        const yScale = this.yScale;

        this.xAxisSelection
            .attr('transform', `translate(0, ${height - margin.bottom})`)
            .call(
                d3.axisBottom(xScale)
                  .ticks(width / 80)
                  .tickSizeOuter(0)
            )
            .call(g => g.selectAll('.tick text').attr('fill', '#666'));

        this.yAxisSelection
            .attr('transform', `translate(${margin.left}, 0)`)
            .call(d3.axisLeft(yScale))
            .call(g => g.selectAll('.tick text').attr('fill', '#666'));

        this.seriesWrapperSelection
            .selectAll('g')
            .data(this.data.series)
            .join('g')
            .append('path')
                .attr('fill', 'none')
                .attr('stroke-width', 1.5)
                .attr('stroke-linejoin', 'round')
                .attr('stroke-linecap', 'round')
                .attr('stroke', d => d.color || '#000')
                .attr('d', d => this.line(d.data));
    }

}

export default LineGraph;
