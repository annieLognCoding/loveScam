function updateUI(data) {
    const {result, danger} = data
    const percentage = Math.floor(result[1] * 100);
    var ctx = document.getElementById('myChart').getContext('2d');
    var resultArea = document.getElementById('realResult');

    var myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Scam', 'Safe'],
            datasets: [{
                label: 'Scam Analysis',
                data: [percentage, 100 - percentage], // Your data array [scam%, safe%]
                backgroundColor: ['#d72c0d', '#00b844'],
                hoverOffset: 4
            }]
        },
        options: {
            cutout: '50%', // Adjust for desired donut thickness
        }
    });
    
    if(percentage > 50){
        var wordsList = document.createElement('ul');
        wordsList.innerHTML = ''; // Clear previous entries
        danger.forEach(word => {
            let li = document.createElement('p');
            li.textContent = word;
            li.style.color = "red";
            wordsList.appendChild(li);
        });
        var susTitle = document.createElement('h1');
        susTitle.innerText = 'Suspicious Words'
        resultArea.appendChild(susTitle);
        resultArea.appendChild(wordsList);
    }
    
}

function uploadFile() {
    const input = document.getElementById('fileInput');
    const data = new FormData();

    if (input.files.length > 0) {
        data.append('image', input.files[0]);

        fetch('/upload', {
            method: 'POST',
            body: data, // No need to set Content-Type header
        })
            .then(response => response.json())
            .then(({ url, data }) => {
                fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => {
                        if (response.ok) return response.text();
                        throw new Error('Something went wrong');
                    })
                    .then(html => document.write(html))
                    .catch(error => console.error('Error:', error));
            });
    }
}




// Function to handle click on confirm buttons
function handleConfirmButtonClick(button) {
    // Get the parent message box
    const box = button.closest('.message-box');
    if (!box) return; // Ensure we have a message box

    // Get the data-type attribute of the clicked button
    const type = button.getAttribute('data-type');

    // Remove existing classes and add the class based on the type
    box.classList.remove('R', 'L', 'C');
    box.classList.add(type);
}

// Attach event listeners to all confirm buttons
document.querySelectorAll('.confirm-button').forEach(button => {
    button.addEventListener('click', function () {
        handleConfirmButtonClick(button);
    });
});

function noChange() {
    document.querySelectorAll('.message-box').forEach(box => {
        // Get the type from the class list of the message box
        let type = Array.from(box.classList).find(cls => ['R', 'L', 'C'].includes(cls));
        if (type == undefined) {
            const align = Array.from(box.classList).find(cls => ['text-center', 'text-left', 'text-right'].includes(cls));
            const textarea = box.querySelector('.message-text');
            if (align === 'text-center') {
                type = 'C';
                box.style.display = 'none';
            }
            else if (align === 'text-left') {
                type = 'L';
                box.style.backgroundColor = 'rgb(16, 15, 15)';
                textarea.style.backgroundColor = 'rgb(16, 15, 15)';
                textarea.style.color = "white";
            }
            if (align === 'text-right') {
                type = 'R';
                box.style.backgroundColor = 'rgb(0, 149, 255)';
                textarea.style.backgroundColor = 'rgb(0, 149, 255)';
                textarea.style.color = "white";
            }
            box.classList.add(type);

        }
        // Push the message object to the messages array
    });
}

function submitChange() {
    const messages = [];

    // Iterate over each message box
    document.querySelectorAll('.message-box').forEach(box => {
        // Get the message text
        const text = box.querySelector('.message-text').value;

        // Get the type from the class list of the message box
        let type = Array.from(box.classList).find(cls => ['R', 'L', 'C'].includes(cls));
        if (type == undefined) {
            const align = Array.from(box.classList).find(cls => ['text-center', 'text-left', 'text-right'].includes(cls));
            if (align === 'text-center') {
                type = 'C';
            }
            else if (align === 'text-left') {
                type = 'L';
            }
            if (align === 'text-right') {
                type = 'R';
            }
            box.classList.add(type);

        }
        // Push the message object to the messages array
        messages.push({ type, text });
    });

    fetch('/process-changes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages })
    })
        .then(response => response.json())
        .then(data => {
            console.log('Processed:', data);
            // Handle response
            return fetch('/get-prediction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data })
            }).then(response => response.json())
                .then(predictionData => {
                    fetch('/result', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ predictionData })

                    })
                        .then(response => response.json())
                        .then(data => updateUI(data))
                        .catch(error => console.error('Error fetching data:', error));
                })
                .catch(error => {
                    console.error('Error in network or parsing:', error);
                });
        })
        .then(response => response.json())
        .then(predictionData => {
            console.log('Prediction:', predictionData);
        })
        .catch(error => {
            console.error('Error in network or parsing:', error);
        });
}



document.addEventListener('DOMContentLoaded', function () {
    const textareas = document.querySelectorAll('.message-text');

    const adjustHeight = (textarea) => {
        textarea.style.height = 'auto';  // Reset the height
        textarea.style.height = textarea.scrollHeight + 'px';  // Set height based on scroll height
    };

    textareas.forEach(textarea => {
        adjustHeight(textarea);  // Adjust height initially
        textarea.addEventListener('input', () => adjustHeight(textarea));  // Adjust on input
        textarea.addEventListener('click', () => {
            textarea.style.backgroundColor = "white";
            textarea.style.color = "black";
        });
        textarea.addEventListener('change', () => adjustHeight(textarea));
    });

    document.querySelectorAll('.confirm-button').forEach(button => {
        button.addEventListener('click', function () {
            const messageBox = this.closest('.message-box');
            const textarea = messageBox.querySelector('.message-text');
            const type = this.getAttribute('data-type');

            switch (type) {
                case 'C':  // Center button pressed, hide the textarea
                    messageBox.style.display = 'none';
                    break;
                case 'L':  // Received button pressed, turn the box black
                    textarea.style.display = 'block';  // Ensure it's visible if previously hidden
                    messageBox.classList.remove('text-left', 'text-right', 'text-center');
                    messageBox.classList.add('text-left');
                    messageBox.style.backgroundColor = 'rgb(16, 15, 15)';
                    adjustHeight(textarea);
                    textarea.style.backgroundColor = 'rgb(16, 15, 15)';  // Ensuring text is visible on black background
                    textarea.style.color = 'white';  // Ensuring text is visible on black background
                    break;
                case 'R':  // Sent button pressed, turn the box blue
                    textarea.style.display = 'block';  // Ensure it's visible if previously hidden
                    messageBox.classList.remove('text-left', 'text-right', 'text-center');
                    messageBox.classList.add('text-right');
                    messageBox.style.backgroundColor = 'rgb(0, 149, 255)';
                    adjustHeight(textarea);
                    textarea.style.backgroundColor = 'rgb(0, 149, 255)';
                    textarea.style.color = 'white';  // Ensuring text is visible on blue background
                    break;
            }
        });
    });


});

