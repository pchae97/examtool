import React, { useState } from "react";
import { Button } from "react-bootstrap";
import useInterval from "./useInterval";

export default function Timer({ target, onEnd }) {
    const [visible, setVisible] = useState(false);
    const [hover, setHover] = useState(false);
    const [timeString, setTimeString] = useState("");

    const updateTimeString = () => {
        const time = Math.round(new Date().getTime() / 1000);
        const remaining = Math.max(target - time, 0);

        const seconds = remaining % 60;
        const minutes = (remaining - seconds) / 60;

        setTimeString(`${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`);

        // five second slack period because we're nice
        if (target - time < -5) {
            onEnd();
        }
    };

    useInterval(updateTimeString, 1000);

    if (!timeString) {
        updateTimeString();
    }

    return (
        <Button
            style={{ minWidth: 80 }}
            onClick={() => setVisible(!visible)}
            variant="outline-light"
            className="ml-auto"
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
        >
            {/* eslint-disable-next-line no-nested-ternary */}
            {visible ? (
                hover ? "Click to hide timer" : timeString
            ) : "Click to show timer"}
        </Button>
    );
}