#include <algorithm>
#include <cmath>
#include <utility>
#include <limits>
#include <stdexcept>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

struct Point { double longitude, latitude; };

struct XY { double x, y; };
constexpr double pi = 3.14159265358979323846;
constexpr double earth_radius = 6371000.0;

std::vector<XY> project(const std::vector<Point>& points) {
    std::vector<XY> plane;
    if (points.empty()) return plane;
    const auto origin = points.front();
    const double scale = earth_radius * pi / 180.0;
    const double longitude_scale = scale * std::cos(origin.latitude * pi / 180.0);
    for (const auto& p : points)
        plane.push_back({(p.longitude - origin.longitude) * longitude_scale,
                         (p.latitude - origin.latitude) * scale});
    return plane;
}

// Distance to the finite segment, not its infinite supporting line.
double distance(XY p, XY a, XY b) {
    const double dx = b.x - a.x, dy = b.y - a.y;
    const double length_squared = dx * dx + dy * dy;
    const double t = length_squared == 0 ? 0 : std::max(0.0, std::min(1.0,
        ((p.x - a.x) * dx + (p.y - a.y) * dy) / length_squared));
    return std::hypot(p.x - a.x - t * dx, p.y - a.y - t * dy);
}

std::vector<std::size_t> simplify(const std::vector<XY>& points, double epsilon) {
    if (points.empty()) return {};
    std::vector<bool> keep(points.size(), false);
    keep.front() = keep.back() = true;
    std::vector<std::pair<std::size_t, std::size_t>> pending{{0, points.size() - 1}};
    while (!pending.empty()) {
        const auto interval = pending.back();
        pending.pop_back();
        const auto first = interval.first, last = interval.second;
        double maximum = epsilon;
        std::size_t split = first;
        for (std::size_t i = first + 1; i < last; ++i) {
            const double deviation = distance(points[i], points[first], points[last]);
            if (deviation > maximum) { maximum = deviation; split = i; }
        }
        if (split != first) {
            keep[split] = true;
            pending.push_back({first, split});
            pending.push_back({split, last});
        }
    }
    std::vector<std::size_t> retained;
    for (std::size_t i = 0; i < keep.size(); ++i)
        if (keep[i]) retained.push_back(i);
    return retained;
}

// Independent postcondition: max over input vertices of distance to output polyline.
// This simple exhaustive audit costs O(n * retained), deliberately explicit for learning.
double max_deviation(const std::vector<XY>& points,
                     const std::vector<std::size_t>& retained) {
    if (retained.size() < 2) return 0;
    double maximum = 0;
    for (const auto p : points) {
        double nearest = std::numeric_limits<double>::infinity();
        for (std::size_t j = 1; j < retained.size(); ++j)
            nearest = std::min(nearest, distance(p, points[retained[j - 1]], points[retained[j]]));
        maximum = std::max(maximum, nearest);
    }
    return maximum;
}

double number(const std::string& text, const std::string& label) {
    try {
        std::size_t used = 0;
        const double value = std::stod(text, &used);
        if (!std::isfinite(value) || text.find_first_not_of(" \t\r", used) != std::string::npos)
            throw std::invalid_argument("invalid number");
        return value;
    } catch (const std::exception&) {
        throw std::runtime_error(label + " must be a finite number");
    }
}

int main(int argc, char** argv) {
    try {
        double epsilon = 0;
        bool epsilon_seen = false;
        std::string input_path, output_path;
        for (int i = 1; i < argc; ++i) {
            const std::string flag = argv[i];
            if (flag != "--epsilon" && flag != "--input" && flag != "--output")
                throw std::runtime_error("unknown argument: " + flag);
            if (++i >= argc) throw std::runtime_error("missing value for " + flag);
            if (flag == "--epsilon") {
                if (epsilon_seen) throw std::runtime_error("duplicate --epsilon");
                epsilon = number(argv[i], "epsilon");
                epsilon_seen = true;
            } else {
                auto& path = flag == "--input" ? input_path : output_path;
                if (!path.empty()) throw std::runtime_error("duplicate " + flag);
                path = argv[i];
                if (path.empty()) throw std::runtime_error("empty path for " + flag);
            }
        }
        if (!epsilon_seen) throw std::runtime_error("required: --epsilon METRES [--input CSV] [--output CSV]");
        if (epsilon < 0) throw std::runtime_error("epsilon must be non-negative");
        std::ifstream input_file;
        if (!input_path.empty()) {
            input_file.open(input_path);
            if (!input_file) throw std::runtime_error("cannot open input: " + input_path);
        }
        std::istream& input = input_path.empty() ? std::cin : input_file;
        std::vector<Point> points;
        std::string line;
        if (!std::getline(input, line)) throw std::runtime_error("CSV header is required");
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line != "longitude,latitude") throw std::runtime_error("expected header longitude,latitude");
        std::size_t line_number = 1;
        while (std::getline(input, line)) {
            ++line_number;
            const std::string label = "line " + std::to_string(line_number);
            const auto comma = line.find(',');
            if (comma == std::string::npos || line.find(',', comma + 1) != std::string::npos)
                throw std::runtime_error(label + ": expected exactly two CSV fields");
            Point p{number(line.substr(0, comma), label + " longitude"),
                    number(line.substr(comma + 1), label + " latitude")};
            if (p.longitude < -180 || p.longitude > 180 || p.latitude < -90 || p.latitude > 90)
                throw std::runtime_error(label + ": coordinate out of range");
            points.push_back(p);
        }
        const auto plane = project(points);
        const auto retained = simplify(plane, epsilon);
        const double deviation = max_deviation(plane, retained);
        if (deviation > epsilon) throw std::runtime_error("projected deviation exceeds epsilon");
        std::ofstream output_file;
        if (!output_path.empty()) {
            output_file.open(output_path);
            if (!output_file) throw std::runtime_error("cannot open output: " + output_path);
        }
        std::ostream& output = output_path.empty() ? std::cout : output_file;
        output << "longitude,latitude\n" << std::setprecision(17);
        for (const auto i : retained)
            output << points[i].longitude << ',' << points[i].latitude << '\n';
        output.flush();
        if (!output) throw std::runtime_error("failed writing output");
        const double ratio = points.empty() ? 0 : 1.0 - static_cast<double>(retained.size()) / points.size();
        std::cerr << std::setprecision(17) << "{\"original\":" << points.size()
                  << ",\"retained\":" << retained.size()
                  << ",\"compression_ratio\":" << ratio
                  << ",\"max_deviation_m\":" << deviation << "}\n";
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
