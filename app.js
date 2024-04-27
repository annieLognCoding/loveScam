const express = require('express');
const multer = require('multer');
const path = require('path');
const sharp = require('sharp');
const { createWorker } = require('tesseract.js');
const Jimp = require('jimp');
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

// GreyScale Image
async function preprocessImage(imageBuffer) {
    const image = await Jimp.read(imageBuffer);

    image
      .grayscale() // convert to grayscale
      .contrast(1) // increase the contrast
      .quality(100); // set JPEG quality
    
    // Return the preprocessed image buffer
    const preprocessedBuffer = await image.getBufferAsync(Jimp.MIME_JPEG);
    return preprocessedBuffer;
  }


app.get("/", (req, res) => {
    res.render('index');
})

app.get("/show", async (req, res) => {
    let [min, count, change] = [-1, 0, false]
    console.log(messages)
    const recieved = messages.map(m => {
        if (m["position"] === "received" && m["text"] != null) {
            change = false
            if(min < 0){
                min = count
            }
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
    count = min;
    for (let r of recieved) {
        if (r != "") {
            text += r["text"].trim() + " "
            if(count < r["pos"]){
                recieved_text.push(text)
                text = ""
                count += 1
            }
        }
    }
    if(text != "") recieved_text.push(text)

    console.log(recieved_text)

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

    res.send({ predictions })
})

app.post('/upload', upload.single('image'), async (req, res) => {
    // Tesseract Worker
    const worker = await createWorker('eng');
    await worker.setParameters({
        tessedit_pageseg_mode: 4
    });
    if (req.file) {
        try {

            const imgBuffer = req.file.buffer;
            const imageWidth = (await sharp(imgBuffer).metadata()).width
            const processedImage = await preprocessImage(imgBuffer) 
            const imageCenter = imageWidth / 2;
            await worker.recognize(processedImage, 'eng')
                .then(({ data: { lines } }) => {                    

                    messages = lines.map(line => {
                        const textCenter = (line.bbox.x0 + line.bbox.x1) / 2;
                        console.log(line.text, line.bbox.x0, imageWidth - line.bbox.x1);
                        // Check if the text center is within a certain threshold of the image center
                        const isCentered = Math.abs(textCenter - imageCenter) < (imageWidth * 0.005); // 0.1% threshold
                        const rightAlign = line.bbox.x0 > (imageWidth - line.bbox.x1); // 5% threshold
                        return {
                            text: line.text,
                            position: rightAlign? 'sent': (isCentered ? 'center' : 'received')
                        };
                    });
                    res.redirect('./show')
                })
                .finally(async () => {
                    await worker.terminate(); 
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
