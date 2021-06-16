class LineGraph {

    constructor({
        width = 300,
        height = 150,
        container,
    }) {
        this.width = width;
        this.height = height;
        this.svgSelection = d3.create('svg').attr("viewBox", [0, 0, width, height]);

        if (container) {
            if (container instanceof HTMLElement) {
                container.appendChild(this.svgSelection.node());
            } else {
                document.querySelector(container).appendChild(this.svgSelection.node());
            }
        }
    }

    setData({ labels, series }) {
        const width = this.width;
        const height = this.height;

        labels = labels.map(d => new Date(d.replace(/(\d{4})(\d{2})/, ($0, $1, $2) => `${$1}-${$2}`)));

        const xScale = d3.scaleUtc()
            .domain(d3.extent(labels))
            .range([0, width]);
        
        const yScale = d3.scaleLinear()
            .domain([
                d3.min(series, d => d3.min(d)),
                d3.max(series, d => d3.max(d))
            ])
            .nice()
            .range([0, height]);

        const line = d3.line()
            .defined(d => !isNaN(d))
            .x(d => x(d))
            .y(d => y(d));
    }

    render() {}

}

export default LineGraph;
