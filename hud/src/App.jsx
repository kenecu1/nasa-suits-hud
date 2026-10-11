import {useState, useEffect} from "react";

function O2Box({label, value}) {
  return <p>{label}: {value}%</p>;
}

function App() {
  const [o2, seto2] = useState(100);

  useEffect(() => {
    const timer = setInterval(() => {
      seto2(Math.round(Math.random() * 100));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return <O2Box label="Primary O2" value={o2} />;
}

export default App;