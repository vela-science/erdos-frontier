#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr std::uint16_t kWitnessThreshold = 16;

struct SearchResult {
  bool witness = false;
  std::uint32_t primes_tested = 0;
  std::uint16_t max_multiplicity = 0;
  std::uint32_t best_prime = 0;
  std::uint32_t best_residue = 0;
  std::vector<std::uint32_t> cuts;
};

std::uint32_t parse_u32(const char* raw, const char* label) {
  const std::string text(raw);
  if (text.empty() ||
      !std::all_of(text.begin(), text.end(), [](const unsigned char character) {
        return character >= '0' && character <= '9';
      })) {
    throw std::runtime_error(std::string(label) + " is not an unsigned integer");
  }
  std::size_t consumed = 0;
  const auto value = std::stoull(text, &consumed, 10);
  if (consumed != text.size() ||
      value > std::numeric_limits<std::uint32_t>::max()) {
    throw std::runtime_error(std::string(label) + " is out of range");
  }
  return static_cast<std::uint32_t>(value);
}

std::vector<std::uint32_t> primes_in_range(
    const std::uint32_t range_start,
    const std::uint32_t range_end) {
  std::vector<bool> prime(static_cast<std::size_t>(range_end) + 1, true);
  if (!prime.empty()) prime[0] = false;
  if (prime.size() > 1) prime[1] = false;
  for (std::uint32_t candidate = 2;
       static_cast<std::uint64_t>(candidate) * candidate <= range_end;
       ++candidate) {
    if (!prime[candidate]) continue;
    for (std::uint64_t multiple =
             static_cast<std::uint64_t>(candidate) * candidate;
         multiple <= range_end;
         multiple += candidate) {
      prime[static_cast<std::size_t>(multiple)] = false;
    }
  }

  std::vector<std::uint32_t> result;
  for (std::uint32_t candidate = std::max<std::uint32_t>(2, range_start);
       candidate <= range_end;
       ++candidate) {
    if (prime[candidate]) result.push_back(candidate);
  }
  return result;
}

SearchResult search(
    const std::uint32_t range_start,
    const std::uint32_t range_end) {
  if (range_start > range_end) {
    throw std::runtime_error("range start exceeds range end");
  }

  SearchResult result;
  const auto primes = primes_in_range(range_start, range_end);
  result.primes_tested = static_cast<std::uint32_t>(primes.size());

  for (const auto prime : primes) {
    // This verifier deliberately uses the residue itself as an array index.
    // It therefore shares no hash function, collision handling, generation
    // table, or primality implementation with the frozen verifier.
    std::vector<std::uint16_t> multiplicity(prime, 0);
    std::vector<std::uint32_t> touched;
    touched.reserve(prime);

    std::uint64_t factorial = 1;
    for (std::uint32_t cut = 0; cut < prime; ++cut) {
      if (cut != 0) factorial = (factorial * cut) % prime;
      const auto residue = static_cast<std::uint32_t>(factorial);
      if (multiplicity[residue] == 0) touched.push_back(residue);
      ++multiplicity[residue];
    }

    std::uint16_t local_max = 0;
    std::uint32_t local_residue = 0;
    for (const auto residue : touched) {
      const auto count = multiplicity[residue];
      if (count > local_max ||
          (count == local_max && residue < local_residue)) {
        local_max = count;
        local_residue = residue;
      }
    }

    // Updating only on a strict increase preserves the earliest-prime tie
    // rule because primes are visited in ascending order.
    if (local_max > result.max_multiplicity) {
      result.max_multiplicity = local_max;
      result.best_prime = prime;
      result.best_residue = local_residue;
    }
    if (local_max >= kWitnessThreshold) {
      result.witness = true;
      result.max_multiplicity = local_max;
      result.best_prime = prime;
      result.best_residue = local_residue;
      break;
    }
  }

  std::uint64_t factorial = 1;
  for (std::uint32_t cut = 0; cut < result.best_prime; ++cut) {
    if (cut != 0) factorial = (factorial * cut) % result.best_prime;
    if (factorial == result.best_residue) result.cuts.push_back(cut);
  }
  return result;
}

std::string render(
    const SearchResult& result,
    const std::uint32_t range_start,
    const std::uint32_t range_end) {
  std::ostringstream output;
  output << "schema=canopus.erdos1056-k15-search.v1\n";
  output << "status=" << (result.witness ? "witness" : "negative") << '\n';
  output << "problem=1056\n";
  output << "k=15\n";
  output << "range_start=" << range_start << '\n';
  output << "range_end=" << range_end << '\n';
  output << "primes_tested=" << result.primes_tested << '\n';
  output << "max_multiplicity=" << result.max_multiplicity << '\n';
  output << "best_p=" << result.best_prime << '\n';
  output << "best_residue=" << result.best_residue << '\n';
  output << "cuts=";
  for (std::size_t index = 0; index < result.cuts.size(); ++index) {
    if (index != 0) output << ',';
    output << result.cuts[index];
  }
  output << '\n';
  return output.str();
}

std::string read_candidate(const char* path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) throw std::runtime_error("cannot open candidate artifact");
  std::ostringstream buffer;
  buffer << input.rdbuf();
  if (!input.good() && !input.eof()) {
    throw std::runtime_error("cannot read candidate artifact");
  }
  const auto bytes = buffer.str();
  if (bytes.size() > 65536) {
    throw std::runtime_error("candidate artifact is oversized");
  }
  return bytes;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 4) {
      std::cerr << "usage: independent-verifier RANGE_START RANGE_END ARTIFACT\n";
      return 64;
    }
    const auto range_start = parse_u32(argv[1], "range start");
    const auto range_end = parse_u32(argv[2], "range end");
    const auto recomputed = render(search(range_start, range_end), range_start, range_end);
    const auto retained = read_candidate(argv[3]);
    if (retained != recomputed) {
      std::cerr << "retained artifact differs from independent recomputation\n";
      return 1;
    }
    std::cout << recomputed;
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 70;
  }
}
