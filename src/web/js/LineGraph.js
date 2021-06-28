function mergeSettings(target, source) {
    if (source) {
        for(let attr in target) {
            if (source[attr]) target[attr] = source[attr];
        }
    }
    return target;
}

const textAlignToTextAnchor = {
    left: 'start',
    center: 'middle',
    right: 'end'
};

class LineGraph {

    constructor({
        chart,
        container,
        xAxis,
        yAxis,
        title,
        subtitle,
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
        this._chart = mergeSettings({
            width: containerWidth || 300,
            height: containerHeight || 150,
            padding: [0, 0, 0, 0]   // highchart使用spacing配置，我使用padding
        }, chart);

        // https://api.highcharts.com.cn/highcharts#xAxis
        this._xAxis = mergeSettings({
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            labels: {
                style: {
                    color: '#666',
                }
            }
        }, xAxis);

        // https://api.highcharts.com.cn/highcharts#yAxis
        this._yAxis = mergeSettings({
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            labels: {
                style: {
                    color: '#666',
                }
            }
        }, yAxis);

        // https://api.highcharts.com.cn/highcharts#title
        this._title = mergeSettings({
            text: null,
            align: 'center',
            style: {
                color: '#333',
                fontSize: '18px',
            }
        }, title);

        // https://api.highcharts.com.cn/highcharts#subtitle
        this._subtitle = mergeSettings({
            text: null,
            align: 'center',
            style: {
                color: '#666',
                fontSize: '12px',
            }
        }, subtitle);

        this._title.x = this._chart.width / 2;
        this._title.y = parseFloat(this._title.style.fontSize, 10) * (4 / 3);

        this._subtitle.x = this._title.x;
        this._subtitle.y = this._title.y + 10 + parseFloat(this._subtitle.style.fontSize, 10);

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
        const padding = this._chart.padding;
        const { labels, series } = data;

        series.forEach((item, i) => {
            item.color = item.color || d3.schemeCategory10[i % 10];
        });

        this._data = data;

        this.xScale = d3.scaleUtc()
            .domain(d3.extent(labels))
            .range([padding[3], width - padding[3]]);
        this.xScale.ticks(width / 80);

        this.yScale = d3.scaleLinear()
            .domain([
                d3.min(series, d => d3.min(d.data)),
                d3.max(series, d => d3.max(d.data))
            ])
            .nice()
            .range([height - padding[2], padding[0]]);

        this.line = d3.line()
            .defined(d => !isNaN(d) && d !== null)
            .x((d, i) => this.xScale(labels[i]))
            .y(d => this.yScale(d));
    }

    render() {
        const width = this._chart.width;
        const height = this._chart.height;
        const padding = this._chart.padding;
        const xScale = this.xScale;
        const yScale = this.yScale;

        const [
            xAxisWrapperSelection,
            yAxisWrapperSelection,
            seriesWrapperSelection,
            titleSelection,
            subtitleSelection
        ] = [{
            selector: 'xAxisWrapper',
            tag: 'g',
        }, {
            selector: 'yAxisWrapper',
            tag: 'g',
        }, {
            selector: 'seriesWrapper',
            tag: 'g',
        }, {
            selector: 'title',
            tag: 'text',
        }, {
            selector: 'subtitle',
            tag: 'text',
        }].map(({ selector, tag }) => {
            let selection = this._svgSelection.selectAll(`.${selector}`);
            if (selection.empty()) {
                selection = this._svgSelection.append(tag).classed(selector, true);
            }
            return selection;
        });

        xAxisWrapperSelection
            .attr('transform', `translate(0, ${height - padding[2]})`)
            .call(d3.axisBottom(xScale))
            .call(g => {
                g.selectAll('.domain').attr('stroke', this._xAxis.lineColor);
                g.selectAll('.tick text').attr('fill', this._xAxis.labels.style.color);
                g.selectAll('.tick line').attr('stroke', this._xAxis.tickColor);
            });

        yAxisWrapperSelection
            .attr('transform', `translate(${padding[3]}, 0)`)
            .call(d3.axisLeft(yScale))
            .call(g => {
                g.selectAll('.domain').attr('stroke', this._yAxis.lineColor);
                g.selectAll('.tick text').attr('fill', this._yAxis.labels.style.color);
                g.selectAll('.tick line').attr('stroke', this._yAxis.tickColor);
            });

        seriesWrapperSelection
            .selectAll('g')
            .data(this._data.series)
            .join('g')
            .append('path')
                .attr('fill', 'none')
                .attr('stroke-width', 1.5)
                .attr('stroke-linejoin', 'round')
                .attr('stroke-linecap', 'round')
                .attr('stroke', d => d.color || '#000')
                .attr('d', d => this.line(d.data));

        titleSelection
            .text(this._title.text)
            .attr('fill', this._title.style.color)
            .attr('font-size', this._title.style.fontSize)
            .attr('text-anchor', textAlignToTextAnchor[this._title.align])
            .attr('x', this._title.x)
            .attr('y', this._title.y);

        subtitleSelection
            .text(this._subtitle.text)
            .attr('fill', this._subtitle.style.color)
            .attr('font-size', this._subtitle.style.fontSize)
            .attr('text-anchor', textAlignToTextAnchor[this._subtitle.align])
            .attr('x', this._subtitle.x)
            .attr('y', this._subtitle.y);
        
    }

}

export default LineGraph;
