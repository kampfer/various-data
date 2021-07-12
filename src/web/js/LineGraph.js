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
        tooltip
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
            padding: [10, 10, 15, 10],   // highchart使用spacing配置，我使用padding
            backgroundColor: '#fff',
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
            },
            crosshair: false,
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
            },
            crosshair: false,
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

        this._tooltip = mergeSettings({
            backgroundColor: 'rgba(247,247,247,0.85)',
            borderColor: null,
            borderRadius: 3,
            borderWidth: 1,
            padding: 8,
            style: {
                fontSize: '12px',
                color: '#333'
            }
        }, tooltip);

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

        // 需要保证数据是递增排序的
        let needReverseData = false;
        if (labels[0] > labels[1]) needReverseData = true;

        if (needReverseData) labels.reverse();

        series.forEach((item, i) => {
            // 设置颜色
            item.color = item.color || d3.schemeCategory10[i % 10];
            // 设置marker
            item.marker = mergeSettings({ symbol: 'circle', radius: 3 }, item.marker);
            // 处理图例
            if (item.name) {
                if (!this._legend.items) this._legend.items = [];
                this._legend.items.push({
                    text: item.name,
                    color: item.color
                });
            }
            if (needReverseData) item.data.reverse();
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
        console.log('render');
        const xScale = this.xScale;
        const yScale = this.yScale;

        const [
            backgroundSelection,
            xAxisWrapperSelection,
            yAxisWrapperSelection,
            xCrosshairSelection,
            yCrosshairSelection,
            seriesWrapperSelection,
            titleSelection,
            subtitleSelection,
            legendSelection,
            tooltipSelection,
            plotBackgroundSelection,
        ] = [{
            selector: 'background',
            tag: 'rect',
        }, {
            selector: 'xAxisWrapper',
            tag: 'g',
        }, {
            selector: 'yAxisWrapper',
            tag: 'g',
        }, {
            selector: 'xCrosshair',
            tag: 'path',
            enable: !!this._xAxis.crosshair
        }, {
            selector: 'yCrosshair',
            tag: 'path',
            enable: !!this._yAxis.crosshair
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
        }, {
            selector: 'tooltip',
            tag: 'g',
        }, {
            selector: 'plotBackground',
            tag: 'rect',
        }].map(({ selector, tag, enable }) => {
            if (enable === false) return;
            let selection = this._svgSelection.selectAll(`.${selector}`);
            if (selection.empty()) {
                selection = this._svgSelection.append(tag).classed(selector, true);
            }
            return selection;
        });

        // 背景色
        backgroundSelection
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', this._chart.width)
            .attr('height', this._chart.height)
            .attr('fill', this._chart.backgroundColor);

        // 通过占位rect监听鼠标事件，实现各种交互
        const xRange = xScale.range();
        const yRange = yScale.range();
        plotBackgroundSelection
            .attr('x', xRange[0])
            .attr('y', yRange[1])
            .attr('width', xRange[1] - xRange[0])
            .attr('height', yRange[0] - yRange[1])
            .attr('fill', 'transparent')
            .on('mousemove', (e) => {
                const label = xScale.invert(e.pageX);
                // 只能用bisectLeft、right
                // bisectCenter会把array元素转成数字，导致比对结果错误，不能使用
                const index = d3.bisectLeft(this._data.labels, label);

                const x = xScale(this._data.labels[index]);
                if (this._xAxis.crosshair) {
                    xCrosshairSelection
                        .attr('visibility', 'visible')
                        .attr('d', `M ${x} ${yRange[0]} L ${x} ${yRange[1]}`);
                }

                const yArr = this._data.series.map(({ data }) => yScale(data[index]));
                const yIndex = d3.minIndex(yArr, v => Math.abs(v - e.pageY));
                if (this._yAxis.crosshair) {
                    yCrosshairSelection
                        .attr('visibility', 'visible')
                        .attr('d', `M ${xRange[0]} ${yArr[yIndex]} L ${xRange[1]} ${yArr[yIndex]}`);
                }

                const formatTime = d3.timeFormat('%Y-%m-%d');
                tooltipSelection.call(g => {

                    const data = [{
                        label: this._data.labels[index],
                        values: (this._data.series.map(({ name, data, color }) => ({
                            color,
                            name,
                            value: data[index]
                        })))
                    }];

                    const textSelection = g.selectAll('text')
                        .data(data)
                        .join('text')
                        .attr('fill', this._tooltip.style.color)
                        .call(g => {
                            g.selectAll('tspan.label')
                                .data(d => [d.label])
                                .join('tspan')
                                .classed('label', true)
                                .text(d => formatTime(d))
                                .style('font-size', 10)
                                .attr('x', this._tooltip.padding)
                                .attr('dy', 10 + this._tooltip.padding);

                            g.selectAll('tspan.valueItem')
                                .data(d => d.values)
                                .join('tspan')
                                .classed('valueItem', true)
                                .style('font-size', this._tooltip.style.fontSize)
                                .attr('x', this._tooltip.padding)
                                .attr('dy', parseFloat(this._tooltip.style.fontSize, 10) + 5)
                                .call(g => {
                                    g.selectAll('tspan.legend')
                                        .data(d => [d.color])
                                        .join('tspan')
                                        .classed('legend', true)
                                        .attr('fill', d => d)
                                        .text('● ');
                                    g.selectAll('tspan.name')
                                        .data(d => [d.name])
                                        .join('tspan')
                                        .classed('name', true)
                                        .text(d => `${d}: `);
                                    g.selectAll('tspan.value')
                                        .data(d => [d.value])
                                        .join('tspan')
                                        .classed('value', true)
                                        .style('font-weight', 'bold')
                                        .text(d => d);
                                });
                        });

                    const box = textSelection.node().getBBox();
                    g.selectAll('path')
                        .data(data)
                        .join('path')
                        .attr('d', `M ${this._tooltip.padding} ${this._tooltip.padding} L ${box.width} ${0 + this._tooltip.padding} L ${box.width} ${box.height + this._tooltip.padding} L ${0 + this._tooltip.padding} ${box.height + this._tooltip.padding}`)
                        .attr('fill', 'rgba(0, 0, 0, 0.5)');

                }).attr('transform', `translate(${x}, ${yArr[yIndex]})`);
                
            })
            .on('mouseout', () => {
                if (this._xAxis.crosshair) xCrosshairSelection.attr('visibility', 'hidden');
                if (this._yAxis.crosshair) yCrosshairSelection.attr('visibility', 'hidden');
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
                g.selectAll('.tick line')
                 .attr('fill', 'none')
                 .attr('stroke', this._yAxis.tickColor)
                 .attr('x1', this.xScale.range()[1] - this._yAxis.position[0])
                 .style('shape-rendering', 'crispEdges');
            });

        if (this._xAxis.crosshair) {
            xCrosshairSelection
                .attr('stroke-width', this._xAxis.crosshair.width)
                .attr('stroke', this._xAxis.crosshair.color)
                .style('shape-rendering', 'crispEdges')
                .attr('fill', 'none');
        }

        if (this._xAxis.crosshair) {
            yCrosshairSelection
                .attr('stroke-width', this._yAxis.crosshair.width)
                .attr('stroke', this._yAxis.crosshair.color)
                .style('shape-rendering', 'crispEdges')
                .attr('fill', 'none');
        }

        seriesWrapperSelection
            .selectAll('g')
            .data(this._data.series)
            .join('g')
            .attr('class', (d, i) => `serie-${i}`)
            .call(g => {
                // 绘制折线
                g.append('path')
                    .classed('line', true)
                    .attr('fill', 'none')
                    .attr('stroke-width', 1.5)
                    .attr('stroke-linejoin', 'round')
                    .attr('stroke-linecap', 'round')
                    .attr('stroke', d => d.color || '#000')
                    .attr('d', d => this.line(d.data));

                // 绘制symbol
                const {labels } = this._data;
                function circle(x, y, w, h) {
                    const startPosition = [x, y + h / 2];
                    const rx = w / 2;
                    const ry = h / 2;
                    const xAxsiRotation = 0;
                    const largeArcFlag = 1;
                    const sweepFlag = 1;
                    return `M ${startPosition[0]} ${startPosition[1]}
                            A ${rx} ${ry} ${xAxsiRotation} ${largeArcFlag} ${sweepFlag} ${startPosition[0] + w} ${startPosition[1]}
                            A ${rx} ${ry} ${xAxsiRotation} ${largeArcFlag} ${sweepFlag} ${startPosition[0]} ${startPosition[1]}
                            Z`;
                }
                g.each(function(p) {
                    d3.select(this)
                        .selectAll('path.point')
                        .data(d => d.data)
                        .join('path')
                            .classed('point', true)
                            .attr('fill', p.color)
                            .attr('d', (d, i) => {
                                const x = xScale(labels[i]);
                                const y = yScale(d);
                                const { radius } = p.marker;
                                return circle(x - radius, y - radius, radius * 2, radius * 2);
                            });
                });
            });

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
