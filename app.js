const express = require('express');
const multer = require('multer');
const path = require('path');
const sharp = require('sharp');
const { createWorker } = require('tesseract.js');

const app = express();
const port = 3000;
var messages = {}

app.set('view engine', 'ejs'); //when rendering html, express app will look for ejs files 
app.set('views', path.join(__dirname, '/views'));

// Set up file storage
// multer.memory is used to configure where and how the uploaded files are stored.
const storage = multer.memoryStorage();

/*
upload.single('image') is a middleware provided by Multer that handles the file upload from a form input named image.
    When a file is uploaded, it’s accessible in your route handler as req.file.
*/
const upload = multer({ storage: storage });

// Tesseract Worker

app.get("/", (req, res) => {
    res.render('index');
})

app.get("/show", async (req, res) => {
    let [count, change] = [0, false]

    const recieved = messages.map(m => {
        if (m["position"] === "recieved" && m["text"] != null) {
            change = false
            return {
                text: m["text"],
                pos: count
            }
        } else if (!change) {
            count += 1;
            change = true
        }
        return ""

    })
    var text = ""
    recieved_text = []
    count = 0
    for (let r of recieved) {
        if (r != "" && count < r["pos"]) {
            recieved_text.push(text)
            text = ""
            count += 1
        }
        if (r != "") {
            text += r["text"].trim() + " "
        }
    }

    const predictions = await Promise.all(recieved_text.map(async text => {
        const response = await fetch('http://localhost:5001/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        }).catch(err => console.error('Error when calling Flask API:', err));

        if (response.ok) {
            const data = await response.json();
            return data
        } else {
            console.error('Failed to fetch:', response.statusText);
        };
    }));

    let judge = ""
    for (let pred of predictions) {
        if (pred == 1) {
            judge = "Scam!"
            break;
        } else {
            judge = "Not Scam!"
        }
    }

    res.send({ judge })
})

app.post('/upload', upload.single('image'), async (req, res) => {
    // Initialize the worker
    const worker = await createWorker('eng');
    await worker.setParameters({
        tessedit_pageseg_mode: 4
    });
    if (req.file) {
        try {

            const imgBuffer = req.file.buffer;
            const imageWidth = (await sharp(imgBuffer).metadata()).width

            await worker.recognize(req.file.buffer, 'eng')
                .then(({ data: { lines } }) => {
                    console.log(lines)
                    messages = lines.map(line => {
                        // console.log(`line X0: ${line.bbox.x0}, Image Width / 4: ${imageWidth / 4}`);
                        return {
                            text: line.text,
                            position: line.bbox.x0 > 170 ? 'sent' : 'received'
                        };
                    });
                    res.redirect('./show')
                })
                .finally(async () => {
                    await worker.terminate(); // Ensure worker is terminated after processing
                });

            // Recognize text from image
            // Terminate the worker
        } catch (error) {
            console.error(error);
            res.status(500).send('Error processing the image.');
        }
    } else {
        res.status(400).send('No file uploaded.');
    }
});

app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
