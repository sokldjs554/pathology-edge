#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <algorithm>
#include <atomic>
#include <cstring>
#include <thread>
#include <vector>

namespace py = pybind11;
py::array_t<uint8_t> extract(py::array_t<uint8_t, py::array::c_style> image,
                            py::array_t<int64_t, py::array::c_style> xy,
                            int size, int threads) {
    auto im = image.request(), coords = xy.request();
    if (im.ndim != 3 || im.shape[2] != 3 || coords.ndim != 2 || coords.shape[1] != 2 || size <= 0 || threads < 1 || threads > 64)
        throw std::invalid_argument("Expected contiguous RGB, Nx2 coordinates, positive size, 1..64 threads");
    const auto h = im.shape[0], w = im.shape[1], n = coords.shape[0];
    auto* src = static_cast<uint8_t*>(im.ptr);
    auto* c = static_cast<int64_t*>(coords.ptr);
    for (ssize_t i=0; i<n; ++i)
        if(c[2*i]<0 || c[2*i+1]<0 || c[2*i]>=w || c[2*i+1]>=h)
            throw std::invalid_argument("Coordinate outside image");
    py::array_t<uint8_t> out({n, ssize_t(size), ssize_t(size), ssize_t(3)});
    auto* dst = out.mutable_data();
    {
        py::gil_scoped_release release;
        std::atomic<ssize_t> next{0};
        auto worker = [&]() {
            for (ssize_t i=next.fetch_add(1); i<n; i=next.fetch_add(1)) {
                auto* patch = dst + i*size*size*3;
                std::fill(patch, patch+size*size*3, uint8_t(255));
                const auto x=c[2*i], y=c[2*i+1];
                for(ssize_t row=0; row<std::min(ssize_t(size),h-y); ++row)
                    std::memcpy(patch+row*size*3, src+((y+row)*w+x)*3, std::min(ssize_t(size),w-x)*3);
            }
        };
        if(threads==1) worker();
        else {
            std::vector<std::thread> pool;
            // Join existing workers even if thread construction fails.
            try { for(int i=0; i<std::min(ssize_t(threads),n); ++i) pool.emplace_back(worker); }
            catch(...) { for(auto& t:pool) t.join(); throw; }
            for(auto& t:pool) t.join();
        }
    }
    return out;
}
PYBIND11_MODULE(_patch_cpp,m) {m.def("extract", &extract);}
