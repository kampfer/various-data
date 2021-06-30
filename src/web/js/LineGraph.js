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

const measureText = function () {
    const ctx = document.createElement('canvas').getContext('2d');
    return function (text, font = '10px sans-serif') {
        ctx.font = font;
        return ctx.measureText(text);
    };
}();

class LineGraph {

    constructor({
        chart,
        container,
        xAxis,
        yAxis,
        title,
        subtitle,
        legend,
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
        // width和height包括填充等
        this._chart = mergeSettings({
            width: containerWidth || 300,
            height: containerHeight || 150,
            padding: [10, 10, 15, 10]   // highchart使用spacing配置，我使用padding
        }, chart);

        // https://api.highcharts.com.cn/highcharts#xAxis
        this._xAxis = mergeSettings({
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            tickLength: 6,
            labels: {
                style: {
                    color: '#666',
                    fontSize: '11px',
                }
            }
        }, xAxis);

        // https://api.highcharts.com.cn/highcharts#yAxis
        this._yAxis = mergeSettings({
            lineColor: '#ccd6eb',
            tickColor: '#ccd6eb',
            tickLength: 6,
            labels: {
                style: {
                    color: '#666',
                    fontSize: '11px',
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

        // https://api.highcharts.com.cn/highcharts#legend
        this._legend = mergeSettings({
            align: 'right',
            layout: 'horizontal',
            padding: 20,
            itemStyle: {
                color: '#333',
                fontSize: '12px',
                fontWeight: 'bold'
            },
            symbolWidth: 16,
            symbolHeight: 12,
            symbolPadding: 5,
        }, legend);

        this._title.x = this._chart.width / 2;
        this._title.y = parseFloat(this._title.style.fontSize, 10) + this._chart.padding[0];

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
            // 处理图例
            if (item.name) {
                if (!this._legend.items) this._legend.items = [];
                this._legend.items.push({
                    text: item.name,
                    color: item.color
                });
            }
        });

        this._data = data;

        this.xScale = d3.scaleUtc()
            .domain(d3.extent(labels));

        this.yScale = d3.scaleLinear()
            .domain([
                d3.min(series, d => d3.min(d.data)),
                d3.max(series, d => d3.max(d.data))
            ])
            .nice();

        const yTickFormat = this.yScale.tickFormat();
        const xTickFormat = this.xScale.tickFormat();
        const yTickFont = `${this._yAxis.labels.style.fontSize} sans-serif`;
        const xTickFont = `${this._xAxis.labels.style.fontSize} sans-serif`;
        const maxLengthOfYLabel = Math.ceil(
            Math.max(
                ...this.yScale.domain().map(v => measureText(yTickFormat(v), yTickFont).width)
            )
        );
        const maxLengthOfXLabel = Math.ceil(
            Math.max(
                ...this.xScale.domain().map(v => measureText(xTickFormat(v), xTickFont).width)
            )
        );
        // 高度 - 下填充 - x轴label的最大长度 - x轴刻度线长度 - x轴刻度线与label之间的间距
        // x轴刻度线与label之间的间距 = d3.axis.tickPadding = 3
        // y轴类似
        this._xAxis.position = [0, height - padding[2] - maxLengthOfXLabel - this._xAxis.tickLength - 3];
        this._yAxis.position = [padding[3] + maxLengthOfYLabel + this._yAxis.tickLength + 3, 0];

        this.xScale
            .range([this._yAxis.position[0], width - padding[1]])
            .ticks(width / 80);

        // 抛去标题的高度
        this.yScale.range([
            this._xAxis.position[1],
            padding[0] + this._subtitle.y + (this._legend.items ? this._legend.padding * 2 + parseFloat(this._legend.itemStyle.fontSize, 10) : 0)
        ]);

        this.line = d3.line()
            .defined(d => !isNaN(d) && d !== null)
            .x((d, i) => this.xScale(labels[i]))
            .y(d => this.yScale(d));
    }

    render() {
        const xScale = this.xScale;
        const yScale = this.yScale;

        const [
            xAxisWrapperSelection,
            yAxisWrapperSelection,
            seriesWrapperSelection,
            titleSelection,
            subtitleSelection,
            legendSelection
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
        }, {
            selector: 'legend',
            tag: 'g',
        }].map(({ selector, tag }) => {
            let selection = this._svgSelection.selectAll(`.${selector}`);
            if (selection.empty()) {
                selection = this._svgSelection.append(tag).classed(selector, true);
            }
            return selection;
        });

        xAxisWrapperSelection
            .attr('transform', `translate(${this._xAxis.position.join(',')})`)
            .call(
                d3.axisBottom(xScale)
                  .tickSize(this._xAxis.tickLength)
            )
            .call(g => {
                g.attr('font-size', this._xAxis.labels.style.fontSize);
                g.selectAll('.domain').attr('stroke', this._xAxis.lineColor);
                g.selectAll('.tick text').attr('fill', this._xAxis.labels.style.color);
                g.selectAll('.tick line').attr('stroke', this._xAxis.tickColor);
            });

        yAxisWrapperSelection
            .attr('transform', `translate(${this._yAxis.position.join(',')})`)
            .call(
                d3.axisLeft(yScale)
                  .tickSize(this._yAxis.tickLength)
            )
            .call(g => {
                g.attr('font-size', this._yAxis.labels.style.fontSize);
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

        if (this._legend.items) {
            legendSelection
                .selectAll('g')
                .data(this._legend.items)
                .join('g')
                .call(g => {
                    g.append('rect')
                    .attr('x', 0)
                    .attr('y', 0)
                    .attr('width', this._legend.symbolWidth)
                    .attr('height', this._legend.symbolHeight)
                    .attr('fill', d => d.color);
                    g.append('text')
                    .attr('x', this._legend.symbolWidth + this._legend.symbolPadding)
                    .attr('y', this._legend.itemStyle.fontSize)
                    .call(g => {
                        for(let key in this._legend.itemStyle) {
                            g.style(key, this._legend.itemStyle[key]);
                        }
                    })
                    .text(d => d.text);
                    let position = 0;
                    g.each(function (d, i, nodes) {
                        const box = nodes[i].getBBox();
                        d3.select(this).attr('transform', `translate(${position} ${0})`);
                        position += box.width + 10;
                    });
                });

            const legendBox = legendSelection.node().getBBox();
            const legendPosition = [];
            if (this._legend.align === 'left') {
                legendPosition[0] = this._legend.padding;
            } else if (this._legend.align === 'center') {
                legendPosition[0] = this._chart.width / 2 - legendBox.width / 2;
            } else if (this._legend.align === 'right') {
                legendPosition[0] = this._chart.width - this._legend.padding - legendBox.width;
            }
            legendPosition[1] = this._subtitle.y + this._legend.padding;
            legendSelection.attr('transform', `translate(${legendPosition[0]} ${legendPosition[1]})`);
        }
    }

}

export default LineGraph;
