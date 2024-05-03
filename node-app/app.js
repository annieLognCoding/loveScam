const express = require('express');
const multer = require('multer');
const path = require('path');
const sharp = require('sharp');
const { createWorker } = require('tesseract.js');
const Jimp = require('jimp');
const app = express();
const session = require('express-session');
const bodyParser = require('body-parser');
const apiUrl = process.env.NODE_ENV === 'production' ? 'https://still-depths-53199-9399d44fc361.herokuapp.com' : 'http://localhost:5001';// Body parsing middleware

let messages = []


// Serve static files from the public directory
app.use(express.static(path.join(__dirname, 'public')));
app.use(bodyParser.json());

app.set('view engine', 'ejs'); //when rendering html, express app will look for ejs files 
app.set('views', path.join(__dirname, '/views'));

app.use(session({
    secret: 'secret_key', // Secret key for signing the session ID cookie
    resave: false,
    saveUninitialized: false
}));
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

function getDynamicThreshold(imageWidth, imageHeight) {
    // Base scale factor; this might need tuning based on empirical data
    const baseScaleFactor = 0.05; // 5% of the image width

    // Adjusting the factor based on image height (the taller the image, the smaller the factor)
    const heightAdjustment = Math.max(0.01, 1 - (imageHeight / 2000)); // Example adjustment logic

    // Calculate dynamic threshold
    const dynamicThreshold = baseScaleFactor * heightAdjustment * imageWidth;
    return dynamicThreshold;
}

function getAlign(locs, imageWidth, imageCenter, imageHeight) {
    let textCenters = []
    if (locs.length > 1) {
        for (let i = 1; i < locs.length; i++) {
            loc = locs[i]
            prevLoc = locs[i - 1]
            const { x0, x1, y0, y1, text } = loc;
            const textCenter = (x1 - x0) / 2
            textCenters.push(textCenter)
        }
        const n = textCenters.length
        const mean = textCenters.reduce((a, b) => a + b) / n
        const std = Math.sqrt(textCenters.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / n)
        const threshold = getDynamicThreshold(imageWidth, imageHeight);
        return std > threshold ? "Multiple Senders" : "Single Sender";
    } else if (locs.length == 1) {
        return "Single Sender"
    }
}

function getVerticalThreshold(textHeight, imageHeight) {
    // You could use a fixed percentage of the text height or a small percentage of the image height
    return Math.max(textHeight * 0.5, imageHeight * 0.02); // 30% of text height or 2% of image height, whichever is larger
}

function analyzeTextBlocks(locs, imageHeight) {
    let textBlocks = [];
    let currentBlock = [];

    for (let i = 0; i < locs.length; i++) {
        const { x0, x1, y0, y1, text } = locs[i];
        if (i > 0) {
            const previous = locs[i - 1];
            const previousY1 = previous.y1;
            const verticalThreshold = getVerticalThreshold(previous.y1 - previous.y0, imageHeight);
            // Check if current text is close enough to previous text vertically
            if (y0 - previousY1 < verticalThreshold) {
                // Current text is close enough to the previous, considered the same block
                currentBlock.push({ x0, x1, y0, y1, text });
            } else {
                // Current text is not close enough, start a new block
                if (currentBlock.length > 0) {
                    textBlocks.push(currentBlock);
                }
                currentBlock = [{ x0, x1, y0, y1, text }];
            }
        } else {
            // First text box, initialize the first block
            currentBlock.push({ x0, x1, y0, y1, text });
        }
    }

    // Push the last block if it exists
    if (currentBlock.length > 0) {
        textBlocks.push(currentBlock);
    }

    return textBlocks; // Returns an array of text blocks
}
function getMessageBlocks(textBlocks, figure, imageWidth) {
    if (figure == "Multiple Senders") {
        const imageCenter = imageWidth / 2;
        let messagesLocal = []
        for (let textBlock of textBlocks) {
            let blockString = "";
            const firstBlock = textBlock[0]
            const { x0, x1, y0, y1, text } = firstBlock;
            const textCenter = x0 + ((x1 - x0) / 2);
            const isCentered = Math.abs(textCenter - imageCenter) < (imageWidth * 0.03); // 0.3% threshold
            const rightAlign = x0 > (imageWidth - x1);
            for (let elem of textBlock) {
                blockString += elem.text.trim() + " ";
            }
            const pos = rightAlign ? 'sent' : (isCentered ? 'center' : 'received')
            messagesLocal.push({ text: blockString, position: pos })
        }

        return messagesLocal

    } else {
        let messagesLocal = []
        for (let textBlock of textBlocks) {
            let blockString = "";
            for (let elem of textBlock) {
                blockString += elem.text.trim() + " ";
            }
            messagesLocal.push({ text: blockString, position: 'received' })
        }

        return messagesLocal
    }
}



app.get("/", (req, res) => {
    if (req.session.data) {
        const data = req.session.data;
        delete req.session.data;  // Delete the data right after using it
        res.render('index', { data, danger: null, result: null }); // Pass the data to the template
    } else {
        res.render('index', { data: null, danger: null, result: null }); // Render without data if session data doesn't exist
    }
});



app.post('/upload', upload.single('image'), async (req, res) => {
    // Tesseract Worker
    const worker = await createWorker('eng');
    await worker.setParameters({
        tessedit_pageseg_mode: 4
    });
    if (req.file) {
        try {

            const imgBuffer = req.file.buffer;
            const metadata = await sharp(imgBuffer).metadata()
            const imageWidth = metadata.width
            const imageHeight = metadata.height
            const processedImage = await preprocessImage(imgBuffer)
            const imageCenter = imageWidth / 2;
            await worker.recognize(processedImage, 'eng')
                .then(({ data: { lines } }) => {

                    locs = lines.map(line => {
                        console.log("here", line.text);
                        return {
                            x0: line.bbox.x0,
                            x1: line.bbox.x1,
                            y0: line.bbox.y0,
                            y1: line.bbox.y1,
                            text: line.text
                        }
                    })
                    const figure = getAlign(locs, imageWidth, imageCenter, imageHeight);
                    const textBlocks = analyzeTextBlocks(locs, imageHeight);
                    messages = getMessageBlocks(textBlocks, figure, imageWidth);
                    res.redirect('./show');
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

app.get('/show', (req, res) => {
    const received_text = {};
    const sent_text = {};
    const center_text = {};

    messages.forEach((m, i) => {
        if (m.position === "received" && m.text) {
            received_text[i] = m.text;
        } else if (m.position === "sent" && m.text) {
            sent_text[i] = m.text;
        } else if (m.position === "center" && m.text) {
            center_text[i] = m.text;
        }
    });

    const show_text = messages.map((_, i) =>
        received_text.hasOwnProperty(i) ? ["L", received_text[i]] :
            sent_text.hasOwnProperty(i) ? ["R", sent_text[i]] :
                center_text.hasOwnProperty(i) ? ["C", center_text[i]] :
                    null
    ).filter(Boolean);
    req.session.data = { show_text };
    res.redirect('/');
});

app.post('/process-changes', (req, res) => {
    try {
        const messages = req.body.messages;
        // Here you can process the messages as needed
        // For example, you can save them to a database
        res.json({ success: true, message: 'Changes processed successfully', messages });
    } catch (error) {
        console.error(error);
        res.status(400).json({ success: false, error: 'Invalid data format' });
    }
});

app.post('/get-prediction', async (req, res) => {
    try {
        console.log(`${apiUrl}/predict`)
        const all_text = req.body;
        const messages = all_text.data.messages;
        const response = await fetch(`${apiUrl}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ messages })
        });

        if (response.ok) {
            const data = await response.json();
            req.session.data = { data };
            res.json({ data });// Send response to the client
        } else {
            console.error('Failed to fetch:', response.statusText);
            res.status(response.status).send({ error: 'Failed to fetch from Flask API' }); // Send error response to the client
        }
    } catch (error) {
        console.error('Error:', error);
        res.status(500).send({ error: 'Internal server error' }); // Send error response to the client
    }
});


app.post("/result", (req, res) => {
    console.log(req.body)
    data = req.body.predictionData.data;
    const { danger, result } = data
    res.json({ danger, result, data: null })
})

const port = process.env.PORT || 3000;
app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
});
