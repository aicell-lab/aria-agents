function SuggestedStudies({ setQuestion }) {
    return (
        <div className="mt-4 text-center">
            <div className="text-gray-700 font-semibold mb-2">Suggested Studies:</div>
            <div className="flex flex-wrap justify-center">
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I want to study the effect of osmotic pressure on yeast cells.")}
                >
                    Osmotic pressure on yeast cells
                </button>
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I'm interested in studying the metabolomics of U2OS cells.")}
                >
                    Metabolomics of U2OS cells
                </button>
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I want to investigate the influence of circadian rhythm on the behavior of Drosophila.")}
                >
                    Circadian rhythm in Drosophila
                </button>
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I'm interested in studying the factors affecting photosynthetic efficiency in C4 plants.")}
                >
                    Photosynthetic efficiency in C4 plants
                </button>
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I'm interested in investigating the genetic basis of thermotolerance in extremophiles.")}
                >
                    Thermotolerance in extremophiles
                </button>
                <button
                    className="bg-gray-200 p-2 m-1 rounded-lg cursor-pointer text-lg transition duration-300 ease-in-out transform hover:scale-105"
                    onClick={() => setQuestion("I aim to examine the neural plasticity in adult zebrafish after spinal cord injury.")}
                >
                    Neural plasticity in adult zebrafish
                </button>
            </div>
        </div>
    )
};

// Expose SuggestedStudies globally
window.SuggestedStudies = SuggestedStudies;