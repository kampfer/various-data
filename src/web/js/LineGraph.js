function mergeSettings(target, source) {
    if (source) {
        for(let attr in target) {
            if (source[attr]) target[attr] = source[attr];
        }
    }
}

class LineGraph {

    constructor({
        chart,
        container,
        xAxis,
        yAxis
    }) {

        if (typeof container === 'string') {
            container = document.querySelector(container);
        }

        let containerWidth, containerHeight;
        if (container instanceof HTMLElement) {
            containerWidth = container.offsetWidth;
            containerHeight = container.offsetHeight;
        }

        // https://api.highcharts.com.cn/highcharts#chart
        this._chart = {
            width: containerWidth || 300,
            height: containerHeight || 150,
            spacing: [0, 0, 0, 0]
        };

        // https://api.highcharts.com.cn/highcharts#xAxis
        this._xAxis = {
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            labels: {
                style: {
                    color: '#666',
                }
            }
        };

        // https://api.highcharts.com.cn/highcharts#yAxis
        this._yAxis = {
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            labels: {
                style: {
                    color: '#666',
                }
            }
        };

        mergeSettings(this._chart, chart);
        mergeSettings(this._xAxis, xAxis);
        mergeSettings(this._yAxis, yAxis);

        this._svgSelection = d3.create('svg')
            .attr('viewBox', [0, 0, this._chart.width, this._chart.height])
            .attr('width', this._chart.width)
            .attr('height', this._chart.height);

        if (container instanceof HTMLElement) {
            container.appendChild(this._svgSelection.node());
        }

    }

    node() {
        return this._svgSelection.node();
    }

    setData(data) {
        const width = this._chart.width;
        const height = this._chart.height;
        const spacing = this._chart.spacing;
        const { labels, series } = data;

        this.data = data;

        this.xScale = d3.scaleUtc()
            .domain(d3.extent(labels))
            .range([spacing[3], width - spacing[3]]);
        
        this.yScale = d3.scaleLinear()
            .domain([
                d3.min(series, d => d3.min(d.data)),
                d3.max(series, d => d3.max(d.data))
            ])
            .nice()
            .range([height - spacing[2], spacing[0]]);

        this.line = d3.line()
            .defined(d => !isNaN(d) && d !== null)
            .x((d, i) => this.xScale(labels[i]))
            .y(d => this.yScale(d));
    }

    render() {
        const width = this._chart.width;
        const height = this._chart.height;
        const spacing = this._chart.spacing;
        const xScale = this.xScale;
        const yScale = this.yScale;

        const [
            xAxisWrapperSelection,
            yAxisWrapperSelection,
            seriesWrapperSelection
        ] = ['xAxisWrapper', 'yAxisWrapper', 'seriesWrapper'].map(selector => {
            let selection = this._svgSelection.selectAll(`.${selector}`);
            if (selection.empty()) {
                selection = this._svgSelection.append('g').classed(selector, true);
            }
            return selection;
        });

        xAxisWrapperSelection
            .attr('transform', `translate(0, ${height - spacing[2]})`)
            .call(
                d3.axisBottom(xScale)
                  .ticks(width / 80)
                  .tickSizeOuter(0)
            )
            .call(g => {
                g.selectAll('.domain').attr('stroke', this._xAxis.lineColor);
                g.selectAll('.tick text').attr('fill', this._xAxis.labels.style.color);
                g.selectAll('.tick line').attr('stroke', this._xAxis.tickColor);
            });

        yAxisWrapperSelection
            .attr('transform', `translate(${spacing[3]}, 0)`)
            .call(d3.axisLeft(yScale))
            .call(g => {
                g.selectAll('.domain').attr('stroke', this._yAxis.lineColor);
                g.selectAll('.tick text').attr('fill', this._yAxis.labels.style.color);
                g.selectAll('.tick line').attr('stroke', this._yAxis.tickColor);
            });

        seriesWrapperSelection
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
