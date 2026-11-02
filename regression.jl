using Statistics
using LinearAlgebra
using UMAP
using DataFrames
using Glob

strike_folder = "strike_wise"
picks_folder = "PICKS/*.txt"


picks_folder = glob(picks_folder)
sort(picks_folder)

for p_path in picks_folder
    
end


